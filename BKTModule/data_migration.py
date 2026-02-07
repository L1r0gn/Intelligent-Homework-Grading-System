from django.db import transaction
from django.utils import timezone
from .models import BKTKnowledgeModel, BKTStudentState, LearningTrace, MigrationHistory
from questionManageModule.models import KnowledgePoint
from gradingModule.models import Submission
import logging

logger = logging.getLogger(__name__)


class BKTDataMigrationService:
    """
    BKT数据迁移服务
    负责从现有系统数据迁移到BKT模型
    """
    
    @classmethod
    def migrate_existing_knowledge_points(cls):
        """
        迁移现有的知识点到BKT模型
        """
        migration = MigrationHistory.objects.create(
            migration_type='INITIAL',
            description='迁移现有知识点到BKT模型',
            status='RUNNING'
        )
        
        try:
            knowledge_points = KnowledgePoint.objects.all()
            created_count = 0
            
            for kp in knowledge_points:
                bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
                    knowledge_point=kp,
                    defaults={
                        'p_L0': 0.1,
                        'p_T': 0.3,
                        'p_G': 0.1,
                        'p_S': 0.1,
                        'decay_factor': 0.95
                    }
                )
                if created:
                    created_count += 1
            
            migration.status = 'SUCCESS'
            migration.records_processed = created_count
            migration.completed_at = timezone.now()
            migration.save()
            
            logger.info(f"成功迁移 {created_count} 个知识点到BKT模型")
            return True
            
        except Exception as e:
            migration.status = 'FAILED'
            migration.error_message = str(e)
            migration.completed_at = timezone.now()
            migration.save()
            logger.error(f"知识点迁移失败: {e}")
            return False
    
    @classmethod
    def migrate_existing_submissions(cls):
        """
        将历史提交记录转换为学习轨迹
        """
        migration = MigrationHistory.objects.create(
            migration_type='INITIAL',
            description='迁移历史提交记录到学习轨迹',
            status='RUNNING'
        )
        
        try:
            # 获取所有有效的提交记录
            submissions = Submission.objects.filter(
                status__in=['ACCEPTED', 'WRONG_ANSWER'],
                problem__knowledge_points__isnull=False
            ).select_related('student', 'problem').prefetch_related('problem__knowledge_points')
            
            processed_count = 0
            
            with transaction.atomic():
                for submission in submissions:
                    # 为每个关联的知识点创建学习轨迹
                    for kp in submission.problem.knowledge_points.all():
                        outcome = 'CORRECT' if submission.status == 'ACCEPTED' else 'INCORRECT'
                        
                        LearningTrace.objects.create(
                            student=submission.student,
                            knowledge_point=kp,
                            outcome=outcome,
                            submission_id=submission.id,
                            attempt_time=submission.submitted_time
                        )
                        processed_count += 1
            
            migration.status = 'SUCCESS'
            migration.records_processed = processed_count
            migration.completed_at = timezone.now()
            migration.save()
            
            logger.info(f"成功迁移 {processed_count} 条学习轨迹")
            return True
            
        except Exception as e:
            migration.status = 'FAILED'
            migration.error_message = str(e)
            migration.completed_at = timezone.now()
            migration.save()
            logger.error(f"提交记录迁移失败: {e}")
            return False
    
    @classmethod
    def initialize_student_states(cls):
        """
        初始化学生状态（基于迁移的学习轨迹）
        """
        from .services import BKTService
        
        migration = MigrationHistory.objects.create(
            migration_type='INITIAL',
            description='初始化学生BKT状态',
            status='RUNNING'
        )
        
        try:
            # 获取所有有学习轨迹的学生-知识点组合
            distinct_combinations = LearningTrace.objects.values(
                'student', 'knowledge_point'
            ).distinct()
            
            initialized_count = 0
            
            for combo in distinct_combinations:
                student_id = combo['student']
                kp_id = combo['knowledge_point']
                
                # 初始化学生状态
                BKTService.initialize_student_state(student_id, kp_id)
                initialized_count += 1
            
            migration.status = 'SUCCESS'
            migration.records_processed = initialized_count
            migration.completed_at = timezone.now()
            migration.save()
            
            logger.info(f"成功初始化 {initialized_count} 个学生状态")
            return True
            
        except Exception as e:
            migration.status = 'FAILED'
            migration.error_message = str(e)
            migration.completed_at = timezone.now()
            migration.save()
            logger.error(f"学生状态初始化失败: {e}")
            return False


class BKTParameterInitializationService:
    """
    BKT参数初始化服务
    基于历史数据训练初始参数
    """
    
    @classmethod
    def train_parameters_from_history(cls):
        """
        基于历史学习轨迹训练BKT参数
        """
        from .bkt_engine import BKTEngine
        
        migration = MigrationHistory.objects.create(
            migration_type='PARAMETER_UPDATE',
            description='基于历史数据训练BKT参数',
            status='RUNNING'
        )
        
        try:
            # 按知识点分组处理
            knowledge_points = KnowledgePoint.objects.all()
            trained_count = 0
            
            for kp in knowledge_points:
                # 获取该知识点的所有学习轨迹
                traces = LearningTrace.objects.filter(
                    knowledge_point=kp
                ).order_by('attempt_time')
                
                if traces.count() < 10:  # 数据量不足，跳过
                    continue
                
                # 准备训练数据
                response_sequences = []
                current_sequence = []
                
                for trace in traces:
                    current_sequence.append(trace.outcome == 'CORRECT')
                    
                    # 每10个答题作为一个序列
                    if len(current_sequence) >= 10:
                        response_sequences.append(current_sequence)
                        current_sequence = []
                
                # 添加最后一个序列
                if current_sequence:
                    response_sequences.append(current_sequence)
                
                if len(response_sequences) < 2:  # 序列数不足
                    continue
                
                # 使用BKT引擎估计参数
                engine = BKTEngine({'p_L0': 0.1, 'p_T': 0.3, 'p_G': 0.1, 'p_S': 0.1})
                estimated_params = engine.estimate_parameters(response_sequences)
                
                # 更新BKT模型参数
                bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
                    knowledge_point=kp
                )
                
                bkt_model.p_L0 = estimated_params['p_L0']
                bkt_model.p_T = estimated_params['p_T']
                bkt_model.p_G = estimated_params['p_G']
                bkt_model.p_S = estimated_params['p_S']
                bkt_model.decay_factor = estimated_params['decay_factor']
                bkt_model.training_samples = traces.count()
                bkt_model.last_trained = timezone.now()
                bkt_model.save()
                
                trained_count += 1
            
            migration.status = 'SUCCESS'
            migration.records_processed = trained_count
            migration.completed_at = timezone.now()
            migration.save()
            
            logger.info(f"成功训练 {trained_count} 个知识点的BKT参数")
            return True
            
        except Exception as e:
            migration.status = 'FAILED'
            migration.error_message = str(e)
            migration.completed_at = timezone.now()
            migration.save()
            logger.error(f"BKT参数训练失败: {e}")
            return False