
import os
import torch
import numpy as np
from django.conf import settings
from collections import namedtuple

from userManageModule.models import User
from questionManageModule.models import KnowledgePoint, Problem
from gradingModule.models import Submission

from .dkt_utils import Item, get_student_predictions

import logging
logger = logging.getLogger(__name__)

# 内存中的模型缓存
_dkt_model_cache = None
_knowledge_dim_cache = None
_knowledge_point_map_reverse_cache = None
_knowledge_point_id_to_obj_map_cache = None

def _load_dkt_model_and_mappings():
    """
    加载训练好的DKT模型和知识点维度及映射。
    缓存模型和知识点维度以提高性能。
    """
    global _dkt_model_cache, _knowledge_dim_cache, _knowledge_point_map_reverse_cache, _knowledge_point_id_to_obj_map_cache

    if _dkt_model_cache is not None and _knowledge_dim_cache is not None and _knowledge_point_map_reverse_cache is not None and _knowledge_point_id_to_obj_map_cache is not None:
        return _dkt_model_cache, _knowledge_dim_cache, _knowledge_point_map_reverse_cache, _knowledge_point_id_to_obj_map_cache

    # 1. 获取所有知识点，确定知识点维度和映射
    all_knowledge_points = KnowledgePoint.objects.all().order_by('id')
    
    # 0-indexed map for DKT model input
    knowledge_point_id_to_idx_map = {kp.id: i for i, kp in enumerate(all_knowledge_points)}
    # idx-to-name map for concept_labels
    knowledge_point_idx_to_name_map = {i: kp.name for i, kp in enumerate(all_knowledge_points)}
    # id-to-object map for direct access
    knowledge_point_id_to_obj_map = {kp.id: kp for kp in all_knowledge_points}

    knowledge_dim = len(all_knowledge_points)

    # 2. 初始化 DKT 模型
    from dkt_app.models import DKTModel,DKT
    dkt_model = DKT(knowledge_dim)

    # 3. 加载训练好的权重
    model_path = os.path.join(settings.BASE_DIR, 'dkt_app', 'trained_models', 'dkt_model.pth')
    if not os.path.exists(model_path):
        logger.error(f"未找到训练好的 DKT 模型：{model_path}。请先运行 `python manage.py train_dkt`。")
        return None, None, None, None # Indicate failure

    # Ensure model is on CPU if not GPU is available or for deployment
    dkt_model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    dkt_model.eval() # 设置模型为评估模式

    _dkt_model_cache = dkt_model
    _knowledge_dim_cache = knowledge_dim
    _knowledge_point_map_reverse_cache = knowledge_point_idx_to_name_map
    _knowledge_point_id_to_obj_map_cache = knowledge_point_id_to_obj_map
    
    return _dkt_model_cache, _knowledge_dim_cache, knowledge_point_id_to_idx_map, _knowledge_point_id_to_obj_map_cache


def get_user_mastery_probabilities(user: User) -> dict:
    """
    获取给定用户的每个知识点的最新掌握概率。
    返回一个字典，键为 KnowledgePoint 对象，值为掌握概率 (0-1)。
    """
    dkt_model, knowledge_dim, knowledge_point_id_to_idx_map, knowledge_point_id_to_obj_map = _load_dkt_model_and_mappings()

    if dkt_model is None:
        logger.error("DKT模型加载失败，无法获取掌握度概率。")
        return {}

    # 获取学生的提交记录并构造模型输入
    submissions = Submission.objects.filter(student=user)\
        .select_related('problem')\
        .prefetch_related('problem__knowledge_points')\
        .order_by('submitted_time')

    student_items_list = []
    for sub in submissions:
        problem_knowledge_codes = []
        for kp in sub.problem.knowledge_points.all():
            if kp.id in knowledge_point_id_to_idx_map:
                problem_knowledge_codes.append(knowledge_point_id_to_idx_map[kp.id] + 1) # +1 for 1-indexed

        # 假设及格线是0.6，与训练时保持一致
        binary_score = 0.0
        problem_points = sub.problem.points
        if problem_points and problem_points > 0:
            student_score = sub.score if sub.score is not None else 0.0
            try:
                correct_percentage = float(student_score) / float(problem_points)
                if correct_percentage >= 0.6:
                    binary_score = 1.0
            except (ValueError, ZeroDivisionError) as e:
                logger.warning(f"Error calculating binary score for submission {sub.id}: {e}")
                binary_score = 0.0 # Default to 0 on error

        student_items_list.append(Item(
            exer_id=sub.problem.id,
            score=binary_score,
            knowledge_code=problem_knowledge_codes
        ))

    if not student_items_list:
        logger.info(f"用户 {user.id} 没有提交记录，返回默认掌握度概率。")
        # 如果没有提交记录，默认所有知识点掌握度为0.5 (中等水平)
        default_mastery = {kp_obj: 0.5 for kp_id, kp_obj in knowledge_point_id_to_obj_map.items()}
        return default_mastery

    # 调用推理函数
    try:
        pred_matrix_list, _ = get_student_predictions(dkt_model, student_items_list, knowledge_dim)
        
        # pred_matrix_list 形状为 (num_knowledge_points, num_submissions)
        # 我们需要每个知识点的最终掌握度，即最后一个时间步的预测
        if pred_matrix_list.shape[1] > 0:
            final_mastery_predictions = pred_matrix_list[:, -1] # 获取最后一个时间步的预测
        else:
            final_mastery_predictions = np.full(knowledge_dim, 0.5) # Fallback if no predictions are made

        mastery_probs = {}
        for kp_id, kp_obj in knowledge_point_id_to_obj_map.items():
            kp_idx = knowledge_point_id_to_idx_map[kp_id]
            if kp_idx < len(final_mastery_predictions):
                mastery_probs[kp_obj] = float(final_mastery_predictions[kp_idx])
            else:
                mastery_probs[kp_obj] = 0.5 # Fallback if knowledge point index is out of bounds
        return mastery_probs

    except Exception as e:
        logger.error(f"获取用户 {user.id} DKT 预测时发生错误: {e}")
        # 发生错误时，返回默认掌握度概率
        default_mastery = {kp_obj: 0.5 for kp_id, kp_obj in knowledge_point_id_to_obj_map.items()}
        return default_mastery
