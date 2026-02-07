from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import BKTService
from .data_migration import BKTDataMigrationService, BKTParameterInitializationService
from userManageModule.decorators import jwt_login_required, admin_required
import json
import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)


# ==================== 微信小程序API (使用JWT认证) ====================

@api_view(['GET'])
@jwt_login_required
def wx_student_knowledge_profile(request, student_id):
    """
    获取学生的知识掌握画像（微信小程序）
    """
    try:
        # 验证权限（学生只能查看自己的数据，教师可以查看班级学生数据）
        current_user = request.user
        if current_user.user_attribute == 1 and current_user.id != student_id:
            return Response({
                'success': False,
                'error': '权限不足，无法查看其他学生数据'
            }, status=status.HTTP_403_FORBIDDEN)
        
        profile = BKTService.get_student_knowledge_profile(student_id)
        
        return Response({
            'success': True,
            'data': profile  # 直接返回profile数据
        })
        
    except Exception as e:
        logger.error(f"获取学生知识画像失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@jwt_login_required
def wx_predict_student_performance(request, student_id):
    """
    预测学生在指定知识点上的表现（微信小程序）
    """
    try:
        data = request.data
        knowledge_point_ids = data.get('knowledge_point_ids', [])
        
        if not knowledge_point_ids:
            return Response({
                'success': False,
                'error': '请提供知识点ID列表'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        predictions = BKTService.predict_student_performance(student_id, knowledge_point_ids)
        
        return Response({
            'success': True,
            'data': predictions
        })
        
    except Exception as e:
        logger.error(f"预测学生表现失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@jwt_login_required
def wx_class_knowledge_analytics(request, class_id):
    """
    获取班级知识点掌握分析（微信小程序）
    """
    try:
        # 验证权限（只有教师可以查看班级数据）
        current_user = request.user
        if current_user.user_attribute < 2:
            return Response({
                'success': False,
                'error': '权限不足，只有教师可以查看班级分析'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 更新班级分析数据
        from userManageModule.models import className
        current_class = className.objects.get(id=class_id)
        BKTService.update_class_analytics(class_identifier=current_class.code)
        
        # 获取分析结果
        from .models import BKTClassAnalytics
        analytics = BKTClassAnalytics.objects.filter(class_identifier=str(current_class.code))
        
        result = []
        for item in analytics:
            result.append({
                'knowledge_point_id': item.knowledge_point.id,
                'knowledge_point_name': item.knowledge_point.name,
                'student_count': item.student_count,
                'average_mastery': item.average_mastery,
                'mastery_std': item.mastery_std,
                'proficiency_rate': item.proficiency_rate
            })
        
        return Response({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取班级分析失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def wx_process_learning_event(request):
    """
    处理学习事件（微信小程序内部API，由作业批改系统调用）
    """
    try:
        data = request.data
        
        student_id = data.get('student_id')
        knowledge_point_id = data.get('knowledge_point_id')
        is_correct = data.get('is_correct')
        submission_id = data.get('submission_id')
        
        if not all([student_id, knowledge_point_id, is_correct is not None]):
            return Response({
                'success': False,
                'error': '缺少必要参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = BKTService.process_learning_event(
            student_id, knowledge_point_id, is_correct, submission_id
        )
        
        return Response({
            'success': True,
            'data': {
                'mastery_probability': result['student_state'].mastery_probability,
                'probability_change': result['probability_change'],
                'improvement': result['improvement']
            }
        })
        
    except Exception as e:
        logger.error(f"处理学习事件失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== 本地管理系统API (使用Session认证) ====================

@api_view(['GET'])
@login_required
def student_knowledge_profile(request, student_id):
    """
    获取学生的知识掌握画像（管理系统）
    """
    try:
        # 验证权限（学生只能查看自己的数据，教师可以查看班级学生数据）
        current_user = request.user
        if current_user.user_attribute == 1 and current_user.id != student_id:
            return Response({
                'success': False,
                'error': '权限不足，无法查看其他学生数据'
            }, status=status.HTTP_403_FORBIDDEN)
        
        profile = BKTService.get_student_knowledge_profile(student_id)
        
        return Response({
            'success': True,
            'data': profile  # 直接返回profile数据
        })
        
    except Exception as e:
        logger.error(f"获取学生知识画像失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@login_required
def predict_student_performance(request, student_id):
    """
    预测学生在指定知识点上的表现（管理系统）
    """
    try:
        data = request.data
        knowledge_point_ids = data.get('knowledge_point_ids', [])
        
        if not knowledge_point_ids:
            return Response({
                'success': False,
                'error': '请提供知识点ID列表'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        predictions = BKTService.predict_student_performance(student_id, knowledge_point_ids)
        
        return Response({
            'success': True,
            'data': predictions
        })
        
    except Exception as e:
        logger.error(f"预测学生表现失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@login_required
def class_knowledge_analytics(request, class_id):
    """
    获取班级知识点掌握分析（管理系统）
    """
    try:
        # 验证权限（只有教师可以查看班级数据）
        current_user = request.user
        if current_user.user_attribute < 2:
            return Response({
                'success': False,
                'error': '权限不足，只有教师可以查看班级分析'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 更新班级分析数据
        try:
            from userManageModule.models import className
            current_class = className.objects.get(id=class_id)
            BKTService.update_class_analytics(class_identifier=str(current_class.code))
        except Exception as e:
            logger.error(f"更新班级分析数据失败: {e}")
            return Response({
                'success': False,
                'error': '更新班级分析数据失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 获取分析结果
        from .models import BKTClassAnalytics
        analytics = BKTClassAnalytics.objects.filter(class_identifier=str(current_class.code))
        if analytics.exists():
            pass
        else:
            return Response({
                'success': False,
                'error': '班级分析数据不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        result = []
        for item in analytics:
            result.append({
                'knowledge_point_id': item.knowledge_point.id,
                'knowledge_point_name': item.knowledge_point.name,
                'student_count': item.student_count,
                'average_mastery': item.average_mastery,
                'mastery_std': item.mastery_std,
                'proficiency_rate': item.proficiency_rate
            })
        
        return Response({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取班级分析失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@login_required
def knowledge_point_parameters(request, kp_id):
    """
    获取知识点的BKT参数（管理系统，管理员专用）
    """
    try:
        # 验证权限（只有管理员可以查看）
        if request.user.user_attribute < 3:
            return Response({
                'success': False,
                'error': '权限不足，只有管理员可以查看参数'
            }, status=status.HTTP_403_FORBIDDEN)
        
        from .models import BKTKnowledgeModel
        from questionManageModule.models import KnowledgePoint
        
        bkt_model, created = BKTKnowledgeModel.objects.get_or_create(
            knowledge_point_id=kp_id
        )
        
        knowledge_point = KnowledgePoint.objects.get(id=kp_id)
        
        return Response({
            'success': True,
            'data': {
                'knowledge_point': {
                    'id': knowledge_point.id,
                    'name': knowledge_point.name,
                    'subject': knowledge_point.subject.name
                },
                'bkt_parameters': bkt_model.to_dict(),
                'training_samples': bkt_model.training_samples,
                'last_trained': bkt_model.last_trained
            }
        })
        
    except Exception as e:
        logger.error(f"获取知识点参数失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def process_learning_event(request):
    """
    处理学习事件（管理系统内部API，由作业批改系统调用）
    """
    try:
        data = request.data
        
        student_id = data.get('student_id')
        knowledge_point_id = data.get('knowledge_point_id')
        is_correct = data.get('is_correct')
        submission_id = data.get('submission_id')
        
        if not all([student_id, knowledge_point_id, is_correct is not None]):
            return Response({
                'success': False,
                'error': '缺少必要参数'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = BKTService.process_learning_event(
            student_id, knowledge_point_id, is_correct, submission_id
        )
        
        return Response({
            'success': True,
            'data': {
                'mastery_probability': result['student_state'].mastery_probability,
                'probability_change': result['probability_change'],
                'improvement': result['improvement']
            }
        })
        
    except Exception as e:
        logger.error(f"处理学习事件失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@login_required
def migrate_bkt_data(request):
    """
    执行BKT数据迁移（管理系统，管理员专用）
    """
    try:
        # 验证权限（只有管理员可以执行迁移）
        if request.user.user_attribute < 3:
            return Response({
                'success': False,
                'error': '权限不足，只有管理员可以执行数据迁移'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        migration_type = data.get('type', 'full')  # full, knowledge_points, submissions, parameters
        
        results = {}
        
        if migration_type in ['full', 'knowledge_points']:
            results['knowledge_points'] = BKTDataMigrationService.migrate_existing_knowledge_points()
        
        if migration_type in ['full', 'submissions']:
            results['submissions'] = BKTDataMigrationService.migrate_existing_submissions()
        
        if migration_type in ['full', 'states']:
            results['states'] = BKTDataMigrationService.initialize_student_states()
        
        if migration_type in ['full', 'parameters']:
            results['parameters'] = BKTParameterInitializationService.train_parameters_from_history()
        
        return Response({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        logger.error(f"数据迁移失败: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== WEB页面视图 ====================

@login_required
def bkt_student_dashboard(request):
    """
    BKT学生知识追踪仪表板
    """
    return render(request, 'bkt_student_dashboard.html')


@login_required
def bkt_class_dashboard(request):
    """
    BKT班级分析仪表板
    """
    # 验证权限（只有教师及以上权限可以访问）
    if request.user.user_attribute < 2:
        return render(request, 'backend_sys_base_page.html', {
            'error_message': '权限不足，只有教师可以访问班级分析功能'
        })
    
    return render(request, 'bkt_class_dashboard.html')