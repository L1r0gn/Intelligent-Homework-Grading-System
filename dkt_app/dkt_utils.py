import torch
import torch.nn.functional as F
import random
import numpy as np
from collections import namedtuple, defaultdict

# Django model imports
from userManageModule.models import User
from questionManageModule.models import Problem, KnowledgePoint
from gradingModule.models import Submission

# DKT model imports
from .models import DKT
import logging
logger = logging.getLogger(__name__)

# 数据格式定义
Item = namedtuple('Item', ['exer_id', 'score', 'knowledge_code'])

class Data_Loader(object):
    def __init__(self):
        self.data_st = defaultdict(list)
        self.knowledge_dim = 0
        self._load_data_from_django_models()
        self._data_clean()

    def _load_data_from_django_models(self):
        # 获取所有知识点，确定知识点维度
        all_knowledge_points = KnowledgePoint.objects.all().order_by('id')
        knowledge_point_map = {kp.id: i for i, kp in enumerate(all_knowledge_points)}
        self.knowledge_dim = len(all_knowledge_points)

        # 获取所有学生提交记录，按学生和提交时间排序
        submissions = Submission.objects.select_related('student', 'problem').prefetch_related('problem__knowledge_points').order_by('student__id', 'submitted_time')

        #test - pass
        # logger.info(len(submissions))

        current_student_id = None
        student_items_list = []

        for sub in submissions:
            if sub.student.id != current_student_id:
                if current_student_id is not None:
                    self.data_st[current_student_id] = student_items_list
                current_student_id = sub.student.id
                student_items_list = []

            # 获取题目关联的知识点
            problem_knowledge_codes = []
            for kp in sub.problem.knowledge_points.all():
                if kp.id in knowledge_point_map:
                    problem_knowledge_codes.append(knowledge_point_map[kp.id]) # +1 because knowledge_code in tmp.py is 1-indexed
            
            # 将得分转换为DKT模型期望的0或1
            # 假设及格线是0.6，这里需要根据实际情况调整
            # 1. 安全获取满分，防止为 0 或 None
            problem_points = sub.problem.points
            if not problem_points or problem_points <= 0:
                # 策略 A: 如果题目没分，直接视为无效数据，跳过或记为 0
                # 这里选择记为 0，避免中断，但你也可以选择 continue 跳过该条记录
                binary_score = 0.0
            else:
                # 2. 安全获取得分，处理 None 情况
                student_score = sub.score if sub.score is not None else 0.0

                # 3. 计算正确率 (确保转为 float)
                try:
                    # 直接计算百分比得分，不要用 if percentage >= 0.6 这种硬阈值
                    # binary_score = float(student_score) / float(problem_points)
                    binary_score = 1.0 if student_score/problem_points >= 0.6 else 0.0

                except (ValueError, ZeroDivisionError):
                    binary_score = 0.0

            # 将结果加入 Item
            student_items_list.append(Item(
                exer_id=sub.problem.id,
                score=binary_score,
                knowledge_code=problem_knowledge_codes
            ))
        
        # 添加最后一个学生的记录
        if current_student_id is not None:
            self.data_st[current_student_id] = student_items_list

    def _data_clean(self):
        """
        清洗数据：
        1. 移除没有知识点映射 (knowledge_code 为空) 的记录。
        2. 移除清洗后没有任何有效记录的学生（防止训练时除以零）。
        """
        cleaned_data = defaultdict(list)
        removed_records_count = 0
        removed_students_count = 0

        for student_id, items in self.data_st.items():
            valid_items = []
            for item in items:
                # 核心逻辑：如果 knowledge_code 列表不为空，则保留
                if item.knowledge_code:
                    valid_items.append(item)
                else:
                    removed_records_count += 1

            # 只有当该学生还有有效记录时，才加入 cleaned_data
            if valid_items:
                cleaned_data[student_id] = valid_items
            else:
                removed_students_count += 1

        # 更新 self.data_st 为清洗后的数据
        self.data_st = cleaned_data

        logger.info(f"Data cleaning completed. Removed {removed_records_count} records without knowledge points. "
                    f"Removed {removed_students_count} students with no valid sequences. "
                    f"Remaining students: {len(self.data_st)}")


def train(data_st, opts):

    #test - pass
    # logger.info(data_st)

    knowledge_n = opts['knowledge_n']
    epoch_n = opts['epoch_n']
    
    dkt = DKT(knowledge_n)
    optimizer = torch.optim.Adam(dkt.parameters(),lr=0.01,weight_decay=1e-5)
    criterion = torch.nn.MSELoss()

    for epoch in range(epoch_n):
        total_loss = 0
        total_seq_cnt = 0
        students = list(data_st.keys())
        random.shuffle(students)
        
        # MSE = torch.nn.MSELoss() # Not used in original train loop for loss calculation
        # MAE = torch.nn.L1Loss() # Not used in original train loop for loss calculation
        
        score_all = {}
        H = {}

        for student in students:
            total_seq_cnt += 1
            item_list = data_st[student]
            item_num = len(item_list)
            optimizer.zero_grad()
            
            loss = 0
            h = None
            score_all[student] = []

            for item in item_list:
                # 构造 one-hot 题目向量
                knowledge = torch.zeros(knowledge_n)
                for k_code in item.knowledge_code:
                    if 0 <= k_code < knowledge_n:  # 严格检查索引
                        knowledge[k_code] = 1.0

                score = torch.FloatTensor([float(item.score)])  # 这里的 score 建议传百分比

                # 调用新模型
                s_pred, all_logits, h = dkt(knowledge, score, h)

                # 使用 MSELoss 或 BCEWithLogitsLoss
                loss += F.binary_cross_entropy_with_logits(s_pred, score.view_as(s_pred))
                
            H[student] = h
            loss /= item_num
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        print(f'Epoch {epoch+1}: Avg Loss {total_loss/total_seq_cnt:.4f}')
            
    return H, score_all, dkt


def get_student_predictions(dkt_model, student_items, knowledge_n):
    dkt_model.eval()
    pred_matrix_list = []
    exercise_seq = []
    h = None

    with torch.no_grad():
        for item in student_items:
            knowledge = torch.zeros(knowledge_n)
            for code in item.knowledge_code:
                # 重要：Data_Loader 已经映射好了，直接用 code，不要 -1
                if 0 <= code < knowledge_n:
                    knowledge[code] = 1.0

            score = torch.FloatTensor([float(item.score)])
            s, all_logits, h = dkt_model(knowledge, score, h)

            # 记录概率
            probs = torch.sigmoid(all_logits).view(-1).cpu().numpy()
            pred_matrix_list.append(probs)

            main_k_idx = item.knowledge_code[0] if item.knowledge_code else 0
            exercise_seq.append({
                'score': item.score,
                'concept_idx': main_k_idx
            })

    return np.array(pred_matrix_list).T, exercise_seq
