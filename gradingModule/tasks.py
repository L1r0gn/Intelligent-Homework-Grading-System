import json
import logging
import base64
import ipaddress
import os
from urllib.parse import urlparse

from celery import shared_task
from openai import OpenAI
from django.conf import settings  # 确保正确引用 settings

from assignmentAndClassModule.models import AssignmentStatus, Assignment
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


def is_publicly_reachable(url):
    """判断 URL 的主机是否可能被外部服务访问。

    本地回环、私有网段、链路本地地址，大模型侧一律拉不到；
    这类情况下要把图片内联成 base64 传过去，否则批改会一直失败但看不出原因。
    """
    host = (urlparse(url).hostname or '').strip()
    if not host:
        return False
    if host.lower() in ('localhost', '0.0.0.0'):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        # 域名：假定公网可达，仅排除 .local 这类内网域名
        return not host.lower().endswith('.local')


def build_image_payload(submission):
    """
    构造交给多模态模型的图片参数。

    公网可访问时用 URL（省带宽）；否则读本地文件转 base64 data URL。
    返回 None 表示无法提供图片。
    """
    base = str(settings.SERVER_BASE_URL).rstrip('/')
    url = f'{base}/api/v1/submissions/{submission.id}/image/'
    if is_publicly_reachable(url):
        logger.info('图片以 URL 形式提交给模型: %s', url)
        return url

    try:
        path = submission.submitted_image.path
    except (ValueError, NotImplementedError) as e:
        logger.error('无法读取本地图片文件（非本地存储？），且 URL 不可公网访问: %s', e)
        return None

    encoded = encode_image_to_base64(path)
    if not encoded:
        return None

    ext = os.path.splitext(path)[1].lstrip('.').lower() or 'png'
    mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
    logger.info('图片地址不可公网访问（%s），改用 base64 内联', url)
    return f'data:{mime};base64,{encoded}'


def grade_submission_with_ai(standard_answer, total_score, submission_id=None, assignment_status_id=None, custom_prompt=None):
    """
    【合并后的核心函数】
    实现"重载"效果：可以通过 submission_id 或 assignment_status_id 调用。
    优先使用 submission_id。
    
    Args:
        standard_answer (str): 标准答案文本，用于与学生答案进行比对
        total_score (int/float): 题目总分，AI将在此范围内进行评分
        submission_id (int, optional): 提交记录ID，用于直接获取提交信息
        assignment_status_id (int, optional): 作业状态ID，通过状态获取对应的提交信息
        custom_prompt (str, optional): 教师自定义的评分提示词，用于增强批改反馈
    
    Returns:
        str/None: 返回AI评分的JSON格式结果字符串，包含score和justification字段；
                 如果调用失败则返回None
                
    功能说明:
        1. 根据提供的ID获取对应的提交对象
        2. 构造AI评分prompt，包含标准答案、总分、自定义提示词等信息
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

    # 图片参数：公网可达走 URL，内网/本地自动转 base64（否则模型侧拉不到图）
    image_url = build_image_payload(submission)
    if not image_url:
        logger.error('❌ 无法构造图片参数，跳过 AI 批改（submission=%s）', submission_id)
        return None

    # 构建自定义提示词部分
    custom_prompt_section = ""
    if custom_prompt and custom_prompt.strip():
        custom_prompt_section = f"""
    # 教师特别要求（请优先严格按照此要求评分）
    {custom_prompt}

    """
        logger.info(f"使用自定义提示词: {custom_prompt[:100]}...")

    # prompt = f"""
    # # 角色
    # 你是一名经验丰富、严格公正的阅卷老师。
    # # 任务
    # 请根据提供的"标准答案"，对"学生提交的答案图片"进行分析和打分。
    # # 上下文
    # - 题目总分: {total_score}分
    # - 标准答案: ```{standard_answer}```
    # - 评分要求 {custom_prompt_section}# 评分要求
    # 1.  仔细阅读并比对"标准答案"和"学生提交的答案图片"。
    # 2.  识别出学生答对的关键得分点。
    # 3.  识别出学生遗漏的、或回答错误的地方。
    # 4.  综合分析，给出一个合理的分数。分数必须是整数。
    # 5.  用简洁的语言给出评分的理由。
    # 6.  对于理科题目（数学、物理、化学等），请重点关注学生的解题思维链（chain of thought），
    # 分析学生的解题思路是否清晰、逻辑是否正确、步骤是否完整。即使最终答案有误，如果解题过程正确
    # 也应给予部分分数，并在评语中指出思维链的优点和不足。
    # # 输出格式
    # 请严格按照以下 JSON 格式返回你的评分结果，不要包含任何额外的解释或文字。
    # {{
    #   "score": <你给出的分数 (整数)>,
    #   "justification": "<你给出的评分理由 (字符串)>"
    # }}
    # """

    # 3. 调用 AI 接口
    client = OpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.OPENROUTER_API_KEY,  # 确保 settings 里有这个 KEY
    )
    import gradingModule.skills
    skill = gradingModule.skills.get_vlm_skill_config(total_score, standard_answer)

    # 4. 处理结果
    try:
        completion = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[
                {
                    "role": "system",
                    "content": f"# 角色\n{skill['role_definition']}\n\n# 执行工作流\n" + "\n".join(
                        skill['workflow_steps'])
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": skill['core_prompt'] + "\n\n请严格按照 JSON 格式返回评分结果。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
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


def _run_grading(submission_id=None):
    """
    【批改主流程】（同步执行体，由 Celery 任务包装）

    状态流转（唯一约定，见 gradingModule.models.Submission）：
        PENDING --任务接手--> GRADING --出结果--> GRADED
                                           \\--异常--> RUNTIME_ERROR
    """
    #============初始化==============
    assignment = None
    assignment_status = None
    submission = None
    problem = None
    custom_prompt = None  # 自定义评分提示词
    #===============================
    # 1. 获取 Submission 对象和上下文
    try:
        if submission_id:
            submission = Submission.objects.get(id=submission_id)
            # 如果是单独提交，题目直接来自 submission
            problem = submission.problem
            # 尝试获取关联的 Assignment（通过 AssignmentStatus）
            try:
                assignment_status = AssignmentStatus.objects.filter(submission=submission).first()
                if assignment_status:
                    assignment = assignment_status.assignment
                    custom_prompt = assignment.custom_prompt
                    logger.info(f"获取到作业关联的自定义提示词: {custom_prompt[:50] if custom_prompt else '无'}...")
            except Exception as e:
                logger.warning(f"未找到关联的作业: {e}")
        else:
            logger.error("❌ 任务调用错误：未提供 submission id")
            return
    except Exception as e:
        logger.error(f"❌ 获取submissions对象失败: {e}")
        return

    # 检查数据
    if not submission or not problem:
        logger.error("❌ 数据不完整，无法评分")
        if submission:
            submission.status = Submission.STATUS_RUNTIME_ERROR
            submission.save(update_fields=['status'])
        return

    # 状态推进：任务已经接手，标记为「批改中」。
    # 过去从不写 GRADING，前端轮询永远看不到这一步，只能一直显示"待批改"直到跳变。
    submission.status = Submission.STATUS_GRADING
    submission.save(update_fields=['status'])

    # 2. 路由评分逻辑
    # A. 选择题 (文本匹配)
    if problem.problem_type.name == "选择":
        logger.info('正在判选择题...')

        # 检查是否有选择答案
        if not submission.choose_answer:
            # 未作答也是一次有效的判定结果：已批改、0 分
            submission.status = Submission.STATUS_GRADED
            submission.score = 0
            submission.justification = '错误：未选择答案'
            logger.info("❌ 选择题未选择答案")
            submission.save(update_fields=['status', 'score', 'justification'])
            return

        student_choose = submission.choose_answer

        # 检查是否有标准答案（题目配置问题，不是学生的错，标为运行错误待人工处理）
        if not problem.answer or not problem.answer.content:
            submission.status = Submission.STATUS_RUNTIME_ERROR
            submission.justification = '错误：该题未设置标准答案'
            logger.error("❌ 选择题未设置标准答案")
            submission.save(update_fields=['status', 'justification'])
            return

        # 比较答案
        logger.info(f'标准答案: {problem.answer.content} | 学生答案: {student_choose}')
        # 对错不再单独占状态位：两种情况都是「已批改」，由分数派生 is_correct
        submission.status = Submission.STATUS_GRADED
        if student_choose.upper() == problem.answer.content.upper():
            submission.score = problem.points
            submission.justification = '答案正确'
            logger.info("✅ 选择题 - 答案正确")
        else:
            submission.score = 0
            submission.justification = f'正确答案是 {problem.answer.content}'
            logger.info("❌ 选择题 - 答案错误")

        # 保存
        submission.save(update_fields=['status', 'score', 'justification'])

        # === 核心：更新知识点掌握度 ===
        if MasteryService:
            MasteryService.update_mastery_after_grading(submission)
        
        # === BKT：更新贝叶斯知识追踪 ===
        if BKTService and problem.knowledge_points.exists():
            is_correct = submission.is_correct
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
        submission.status = Submission.STATUS_RUNTIME_ERROR
        submission.justification = '错误：未找到提交的图片'
        submission.save(update_fields=['status', 'justification'])
        return

    # 调用上面合并后的 AI 函数，传入自定义提示词
    ai_response_str = grade_submission_with_ai(
        standard_answer=problem.answer.explanation if problem.answer else "略",
        total_score=problem.points,
        submission_id=submission.id,  # 明确传入 submission_id
        custom_prompt=custom_prompt  # 传入教师自定义提示词
    )

    if ai_response_str is None:
        submission.status = Submission.STATUS_RUNTIME_ERROR
        submission.justification = 'AI 评分服务暂时不可用'
        submission.save(update_fields=['status', 'justification'])
        return

    try:
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        submission.status = Submission.STATUS_GRADED
        submission.save(update_fields=['status', 'score', 'justification'])

        logger.info(f"✅ AI 批改完成，分数: {submission.score}")

        # === 核心：更新知识点掌握度 ===
        if MasteryService:
            MasteryService.update_mastery_after_grading(submission)
        
        # === BKT：更新贝叶斯知识追踪 ===
        if BKTService and problem.knowledge_points.exists():
            # 判定阈值由 Submission.CORRECT_RATIO_THRESHOLD 统一提供，
            # 不再在此处硬编码 0.6，避免和掌握度分析的口径分叉
            is_correct = submission.is_correct
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
        submission.status = Submission.STATUS_RUNTIME_ERROR
        submission.justification = f'解析 AI 结果失败: {e}'
        submission.save(update_fields=['status', 'justification'])
        logger.error(f"❌ 解析失败: {e}")


@shared_task
def process_and_grade_submission(submission_id=None):
    """Celery 任务入口：调用时只传 submission_id。

    用一层包装而不是把 try/except 塞进主流程，是为了兜住"未预料的异常"：
    一旦异常把状态卡在 GRADING，前端轮询永远等不到结果。
    """
    try:
        _run_grading(submission_id=submission_id)
    except Exception as exc:
        logger.exception("❌ 批改任务异常终止（submission=%s）: %s", submission_id, exc)
        if submission_id:
            # 只有还没进终态的才标记失败，避免覆盖已经写好的批改结果
            Submission.objects.filter(id=submission_id).exclude(
                status__in=Submission.STATUS_TERMINAL
            ).update(status=Submission.STATUS_RUNTIME_ERROR)
        raise
