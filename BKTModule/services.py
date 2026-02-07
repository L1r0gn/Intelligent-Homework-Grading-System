from django.db import transaction
from django.utils import timezone
from .models import BKTKnowledgeModel, BKTStudentState, LearningTrace, BKTClassAnalytics
from .bkt_engine import BKTEngine
from questionManageModule.models import KnowledgePoint
import logging

logger = logging.getLogger(__name__)


class BKTService:
    """
    BKT核心服务类
    提供BKT相关的业务逻辑接口
    """
    
    @classmethod
    def initialize_student_state(cls, student_id: int, knowledge_point_id: int) -> BKTStudentState:
        """
        初始化学生在某个知识点上的BKT状态
        
        Args:
            student_id: 学生ID
            knowledge_point_id: 知识点ID
            
        Returns:
            BKTStudentState实例
        """
        # 获取或创建BKT模型参数
        bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
            knowledge_point_id=knowledge_point_id
        )
        
        # 获取该学生在此知识点上的所有历史答题记录
        historical_traces = LearningTrace.objects.filter(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id
        ).order_by('attempt_time')
        
        # 如果没有历史记录，使用初始参数
        if not historical_traces.exists():
            initial_prob = bkt_model.p_L0
            total_attempts = 0
            correct_attempts = 0
            streak_length = 0
        else:
            # 基于历史记录计算初始状态
            initial_prob = bkt_model.p_L0
            total_attempts = historical_traces.count()
            correct_attempts = historical_traces.filter(outcome='CORRECT').count()
            
            # 计算连续正确次数
            streak_length = 0
            recent_traces = historical_traces.order_by('-attempt_time')[:5]
            for trace in recent_traces:
                if trace.outcome == 'CORRECT':
                    streak_length += 1
                else:
                    break
        
        # 创建或更新学生状态
        student_state, created = BKTStudentState.objects.update_or_create(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id,
            defaults={
                'mastery_probability': initial_prob,
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'streak_length': streak_length
            }
        )
        
        # 如果有历史记录，重新计算掌握概率
        if historical_traces.exists():
            cls._recalculate_mastery_from_history(student_state, bkt_model, historical_traces)
        
        return student_state
    
    @classmethod
    def _recalculate_mastery_from_history(cls, student_state: BKTStudentState, 
                                        bkt_model: BKTKnowledgeModel, 
                                        traces) -> None:
        """
        基于历史轨迹重新计算掌握概率
        """
        engine = BKTEngine(bkt_model.to_dict())
        current_prob = bkt_model.p_L0
        
        for trace in traces:
            is_correct = trace.outcome == 'CORRECT'
            current_prob = engine.update_mastery_probability(current_prob, is_correct)
        
        student_state.mastery_probability = current_prob
        student_state.predicted_performance = engine.predict_next_performance(current_prob)
        student_state.save()
    
    @classmethod
    def process_learning_event(cls, student_id: int, knowledge_point_id: int, 
                             is_correct: bool, submission_id: int = None) -> dict:
        """
        处理学习事件（学生答题）
        
        Args:
            student_id: 学生ID
            knowledge_point_id: 知识点ID
            is_correct: 答题是否正确
            submission_id: 关联的提交记录ID（可选）
            
        Returns:
            包含更新信息的字典
        """
        try:
            with transaction.atomic():
                # 1. 获取或初始化学生状态
                student_state = cls.initialize_student_state(student_id, knowledge_point_id)
                
                # 2. 获取BKT参数
                bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
                    knowledge_point_id=knowledge_point_id
                )
                
                # 3. 记录学习轨迹
                outcome = 'CORRECT' if is_correct else 'INCORRECT'
                trace = LearningTrace.objects.create(
                    student_id=student_id,
                    knowledge_point_id=knowledge_point_id,
                    outcome=outcome,
                    submission_id=submission_id
                )
                
                # 4. 更新掌握概率
                old_probability = student_state.mastery_probability
                new_probability = student_state.update_from_outcome(outcome, bkt_model.to_dict())
                
                # 5. 更新轨迹的前后概率
                trace.predicted_mastery_before = old_probability
                trace.predicted_mastery_after = new_probability
                trace.save()
                
                result = {
                    'student_state': student_state,
                    'learning_trace': trace,
                    'probability_change': new_probability - old_probability,
                    'improvement': new_probability > old_probability,
                    'bkt_params': bkt_model.to_dict()
                }
                
                logger.info(f"BKT处理完成: 学生{student_id}-知识点{knowledge_point_id}, "
                          f"概率变化: {old_probability:.3f}→{new_probability:.3f}")
                
                return result
                
        except Exception as e:
            logger.error(f"BKT学习事件处理失败: {e}")
            raise
    
    @classmethod
    def get_student_knowledge_profile(cls, student_id: int) -> dict:
        """
        获取学生的完整知识掌握画像
        Args:
            student_id: 学生ID
        Returns:
            包含各知识点掌握情况的字典
        """
        # 获取学生的所有BKT状态
        student_states = BKTStudentState.objects.filter(
            student_id=student_id
        ).select_related('knowledge_point', 'knowledge_point__subject')
        
        profile = {
            'student_id': student_id,
            'total_knowledge_points': student_states.count(),
            'knowledge_points': [],
            'summary': {
                'mastered_count': 0,  # 掌握度 > 0.8
                'learning_count': 0,  # 掌握度 0.5-0.8
                'struggling_count': 0,  # 掌握度 < 0.5
                'average_mastery': 0.0
            }
        }
        
        total_mastery = 0
        
        for state in student_states:
            kp_info = {
                'id': state.knowledge_point.id,
                'name': state.knowledge_point.name,
                'subject': state.knowledge_point.subject.name,
                'mastery_probability': state.mastery_probability,
                'total_attempts': state.total_attempts,
                'correct_attempts': state.correct_attempts,
                'predicted_performance': state.predicted_performance,
                'level': cls._classify_mastery_level(state.mastery_probability)
            }
            
            profile['knowledge_points'].append(kp_info)
            total_mastery += state.mastery_probability
            
            # 统计分类
            if state.mastery_probability >= 0.8:
                profile['summary']['mastered_count'] += 1
            elif state.mastery_probability >= 0.5:
                profile['summary']['learning_count'] += 1
            else:
                profile['summary']['struggling_count'] += 1
        
        # 计算平均掌握度
        if student_states.count() > 0:
            profile['summary']['average_mastery'] = total_mastery / student_states.count()
        
        return profile
    
    @classmethod
    def _classify_mastery_level(cls, mastery_prob: float) -> str:
        """分类掌握水平"""
        if mastery_prob >= 0.8:
            return 'mastered'
        elif mastery_prob >= 0.5:
            return 'learning'
        else:
            return 'struggling'
    
    @classmethod
    def predict_student_performance(cls, student_id: int, 
                                  knowledge_point_ids: list) -> dict:
        """
        预测学生在指定知识点上的表现
        
        Args:
            student_id: 学生ID
            knowledge_point_ids: 知识点ID列表
            
        Returns:
            预测结果字典
        """
        predictions = {}
        
        for kp_id in knowledge_point_ids:
            try:
                # 获取学生状态
                student_state = BKTStudentState.objects.get(
                    student_id=student_id,
                    knowledge_point_id=kp_id
                )
                
                # 获取BKT参数
                bkt_model = BKTKnowledgeModel.objects.get(knowledge_point_id=kp_id)
                engine = BKTEngine(bkt_model.to_dict())
                
                # 预测表现
                predicted_accuracy = engine.predict_next_performance(
                    student_state.mastery_probability
                )
                
                predictions[kp_id] = {
                    'knowledge_point_id': kp_id,
                    'current_mastery': student_state.mastery_probability,
                    'predicted_accuracy': predicted_accuracy,
                    'confidence_level': cls._calculate_confidence_level(
                        student_state.total_attempts
                    )
                }
                
            except (BKTStudentState.DoesNotExist, BKTKnowledgeModel.DoesNotExist):
                predictions[kp_id] = {
                    'knowledge_point_id': kp_id,
                    'current_mastery': 0.0,
                    'predicted_accuracy': 0.0,
                    'confidence_level': 'low'
                }
        
        return predictions
    
    @classmethod
    def _calculate_confidence_level(cls, attempts: int) -> str:
        """根据答题次数计算置信度等级"""
        if attempts >= 20:
            return 'high'
        elif attempts >= 10:
            return 'medium'
        else:
            return 'low'
    
    @classmethod
    def update_class_analytics(cls, class_identifier: str, class_type: str = 'CLASS'):
        """
        更新班级知识点掌握分析
        
        Args:
            class_identifier: 班级标识符 （班级id）
            class_type: 班级类型 ('CLASS' 或 'GRADE')
        """
        from userManageModule.models import User, className
        
        try:
            # 获取班级学生
            total_student_count = 0
            if class_type == 'CLASS':
                try:
                    class_obj = className.objects.get(code=class_identifier)
                    students = class_obj.members.filter(user_attribute=1)  # 只统计学生
                    total_student_count = students.count()
                except className.DoesNotExist:
                    logger.warning(f"班级 {class_identifier} 不存在")
                    return
            else:
                # 年级级别分析
                students = User.objects.filter(user_attribute=1)  # 所有学生
                total_student_count = students.count()

            # 获取所有知识点
            knowledge_points = KnowledgePoint.objects.all()

            for kp in knowledge_points:
                # 获取该班级所有学生在此知识点上的状态
                student_states = BKTStudentState.objects.filter(
                    student__in=students,
                    knowledge_point=kp
                )
                
                if not student_states.exists():
                    continue
                
                # 计算统计指标
                mastery_values = [state.mastery_probability for state in student_states]
                student_count = len(mastery_values)
                average_mastery = sum(mastery_values) / student_count
                
                # 计算标准差
                if student_count > 1:
                    variance = sum((x - average_mastery) ** 2 for x in mastery_values) / (student_count - 1)
                    mastery_std = variance ** 0.5
                else:
                    mastery_std = 0.0
                
                # 计算熟练率（掌握度>0.8的比例）
                proficient_count = sum(1 for x in mastery_values if x > 0.8)
                proficiency_rate = proficient_count / student_count if student_count > 0 else 0.0
                # 更新或创建班级分析记录
                BKTClassAnalytics.objects.update_or_create(
                    class_identifier=class_identifier,
                    class_type=class_type,
                    knowledge_point=kp,
                    defaults={
                        'average_mastery': average_mastery,
                        'student_count': total_student_count,
                        'mastery_std': mastery_std,
                        'proficiency_rate': proficiency_rate
                    }
                )
            
            logger.info(f"班级 {class_identifier} 的BKT分析更新完成")
        except Exception as e:
            logger.error(f"更新班级分析失败: {e}")
            raise