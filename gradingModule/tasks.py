import json
import logging
import base64
from celery import shared_task
from openai import OpenAI
from django.conf import settings  # 确保正确引用 settings

from assignmentAndClassModule.models import AssignmentStatus
from .models import Submission
# === 导入知识点分析服务 ===
try:
    from .analysis_logic import MasteryService
except ImportError:
    MasteryService = None
    logging.getLogger(__name__).warning(
        "Warning: MasteryService not found. Knowledge mastery features will be disabled.")

# === 导入BKT服务 ===
try:
    from BKTModule.services import BKTService
except ImportError:
    BKTService = None
    logging.getLogger(__name__).warning(
        "Warning: BKTService not found. BKT knowledge tracking features will be disabled.")

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_path):
    """将图片文件编码为 Base64 字符串。"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"❌ 编码图片失败: {e}")
        return None


def grade_submission_with_ai(standard_answer, total_score, submission_id=None, assignment_status_id=None):
    """
    【合并后的核心函数】
    实现"重载"效果：可以通过 submission_id 或 assignment_status_id 调用。
    优先使用 submission_id。
    
    Args:
        standard_answer (str): 标准答案文本，用于与学生答案进行比对
        total_score (int/float): 题目总分，AI将在此范围内进行评分
        submission_id (int, optional): 提交记录ID，用于直接获取提交信息
        assignment_status_id (int, optional): 作业状态ID，通过状态获取对应的提交信息
    
    Returns:
        str/None: 返回AI评分的JSON格式结果字符串，包含score和justification字段；
                 如果调用失败则返回None
                
    功能说明:
        1. 根据提供的ID获取对应的提交对象
        2. 构造AI评分prompt，包含标准答案、总分等信息
        3. 调用阿里云千问VL模型进行图片内容分析和评分
        4. 返回结构化的评分结果
    """
    # 1. 获取 Submission 对象
    if submission_id:
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            logger.error(f"❌ 找不到 submission_id: {submission_id}")
            return None
    elif assignment_status_id:
        try:
            status = AssignmentStatus.objects.get(id=assignment_status_id)
            submission = status.submission
            submission_id = submission.id
        except AssignmentStatus.DoesNotExist:
            logger.error(f"❌ 找不到 assignment_status_id: {assignment_status_id}")
            return None
    else:
        logger.error("❌ 必须提供 submission_id 或 assignment_status_id")
        return None

    # 检查 submission
    if not submission:
        return None

    # 2. 准备 Prompt 和 图片
    logger.info(f'开始 AI 评分，标准答案: {standard_answer}')

    # 优先使用 URL，如果需要也可以切换为 Base64
    image_url = f"{settings.SERVER_BASE_URL}/grading/submission-image/{submission_id}"
    logger.info(f"图片 URL: {image_url}")

    prompt = f"""
    # 角色
    你是一名经验丰富、严格公正的阅卷老师。
    # 任务
    请根据提供的“标准答案”，对“学生提交的答案图片”进行分析和打分。
    # 上下文
    - 题目总分: {total_score}分
    - 标准答案: ```{standard_answer}```
    # 评分要求
    1.  仔细阅读并比对“标准答案”和“学生提交的答案图片”。
    2.  识别出学生答对的关键得分点。
    3.  识别出学生遗漏的、或回答错误的地方。
    4.  综合分析，给出一个合理的分数。分数必须是整数。
    5.  用简洁的语言给出评分的理由。
    # 输出格式
    请严格按照以下 JSON 格式返回你的评分结果，不要包含任何额外的解释或文字。
    {{
      "score": <你给出的分数 (整数)>,
      "justification": "<你给出的评分理由 (字符串)>"
    }}
    """

    # 3. 调用 AI 接口
    client = OpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.OPENROUTER_API_KEY,  # 确保 settings 里有这个 KEY
    )

    # 4. 处理结果
    try:
        completion = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": image_url}
                    ]
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,  # 降低随机性
            timeout=120
        )
        content = completion.choices[0].message.content
        logger.info(f"✅ AI 评分成功！返回内容: {content}")
        return content

    except Exception as e:
        logger.error(f"❌ 调用 AI API 失败: {e}")
        # 如果 API 失败，可以考虑在这里做重试或者返回特定错误格式
        return None


@shared_task
def process_and_grade_submission(assignment_status_id=None, submission_id=None):
    """
    【合并后的 Celery 任务】
    既可以处理作业状态流程 (AssignmentStatus)，也可以处理单纯的提交 (Submission)。
    如果调用时只传一个参数，默认视为 assignment_status_id (兼容旧代码逻辑)。
    """
    #============初始化==============
    assignment_status = None
    submission = None
    problem = None
    #===============================
    # 1. 获取 Submission 对象和上下文
    try:
        if assignment_status_id:
            assignment_status = AssignmentStatus.objects.get(id=assignment_status_id)
            submission = assignment_status.submission
            # 如果是作业，题目来自 assignment
            problem = assignment_status.assignment.problem
        elif submission_id:
            submission = Submission.objects.get(id=submission_id)
            # 如果是单独提交，题目直接来自 submission
            problem = submission.problem
        else:
            logger.error("❌ 任务调用错误：未提供 ID")
            return
    except Exception as e:
        logger.error(f"❌ 获取对象失败: {e}")
        return

    # 检查数据
    if not submission or not problem:
        logger.error("❌ 数据不完整，无法评分")
        if submission:
            submission.status = 'RUNTIME_ERROR'
            submission.save()
        return

    # 2. 路由评分逻辑
    # A. 选择题 (文本匹配)
    if problem.problem_type.name == "选择":
        logger.info('正在判选择题...')

        # 检查是否有选择答案
        if not submission.choose_answer:
            submission.status = 'WRONG_ANSWER'
            submission.score = 0
            submission.justification = f'错误：未选择答案'
            logger.info("❌ 选择题未选择答案")
            submission.save()
            return

        student_choose = submission.choose_answer

        # 检查是否有标准答案
        if not problem.answer or not problem.answer.content:
            submission.status = 'RUNTIME_ERROR'
            submission.justification = '错误：该题未设置标准答案'
            logger.error("❌ 选择题未设置标准答案")
            submission.save()
            return

        # 比较答案
        logger.info(f'标准答案: {problem.answer.content} | 学生答案: {student_choose}')
        if student_choose.upper() == problem.answer.content.upper():
            submission.status = 'GRADED'
            submission.score = problem.points
            logger.info("✅ 选择题 - 答案正确")
        else:
            submission.status = 'WRONG_ANSWER'
            submission.score = 0
            submission.justification = f'正确答案是 {problem.answer.content}'
            logger.info("❌ 选择题 - 答案错误")

        # 保存
        submission.save()
        if assignment_status:
            assignment_status.save()

        # === 核心：更新知识点掌握度 ===
        if MasteryService:
            MasteryService.update_mastery_after_grading(submission)
        
        # === BKT：更新贝叶斯知识追踪 ===
        if BKTService and problem.knowledge_points.exists():
            is_correct = (submission.status == 'GRADED')
            for kp in problem.knowledge_points.all():
                try:
                    BKTService.process_learning_event(
                        student_id=submission.student.id,
                        knowledge_point_id=kp.id,
                        is_correct=is_correct,
                        submission_id=submission.id
                    )
                    logger.info(f"✅ BKT更新成功: 学生{submission.student.id}, 知识点{kp.id}")
                except Exception as e:
                    logger.error(f"❌ BKT处理失败: {e}")
        return

    # B. 主观题 (AI 图片分析)
    logger.info('正在判填空/大题 (AI 图片评分)...')

    # 检查图片
    if not submission.submitted_image:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：未找到提交的图片'
        submission.save()
        return

    # 调用上面合并后的 AI 函数
    ai_response_str = grade_submission_with_ai(
        standard_answer=problem.answer.explanation if problem.answer else "略",
        total_score=problem.points,
        submission_id=submission.id  # 明确传入 submission_id
    )

    if ai_response_str is None:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = 'AI 评分服务暂时不可用'
        submission.save()
        return

    try:
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        submission.status = 'GRADED'
        submission.save()
        if assignment_status: assignment_status.save()

        logger.info(f"✅ AI 批改完成，分数: {submission.score}")

        # === 核心：更新知识点掌握度 ===
        if MasteryService:
            MasteryService.update_mastery_after_grading(submission)
        
        # === BKT：更新贝叶斯知识追踪 ===
        if BKTService and problem.knowledge_points.exists():
            # AI评分的题目，根据得分率判断是否正确（得分率60%以上视为正确）
            is_correct = (submission.score / problem.points) >= 0.6 if problem.points > 0 else False
            for kp in problem.knowledge_points.all():
                try:
                    BKTService.process_learning_event(
                        student_id=submission.student.id,
                        knowledge_point_id=kp.id,
                        is_correct=is_correct,
                        submission_id=submission.id
                    )
                    logger.info(f"✅ BKT更新成功: 学生{submission.student.id}, 知识点{kp.id}")
                except Exception as e:
                    logger.error(f"❌ BKT处理失败: {e}")

    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = f'解析 AI 结果失败: {e}'
        submission.save()
        logger.error(f"❌ 解析失败: {e}")