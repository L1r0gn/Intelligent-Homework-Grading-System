import json
import logging
from celery import shared_task
from openai import OpenAI

from assignmentAndClassModule.models import Assignment, AssignmentStatus
from .models import Submission, Problem
from IntelligentHomeworkGradingSystem import settings
import base64
logger = logging.getLogger(__name__)
def encode_image_to_base64(image_path):
    """将图片文件编码为 Base64 字符串。"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logger.info(f"❌ 编码图片失败: {e}")
        return None


def grade_submission_with_ai(standard_answer, total_score,submission_id):
    """使用的语言模型对OCR文本进行分析和打分。"""
    logger.info('标准答案为', standard_answer)
    image_url = f"http://119.29.152.140:8000/grading/submission-image/{submission_id}"
    # image_url = "http://119.29.152.140:8000/grading/submission-image/1"
    logger.info(image_url)
    # 针对纯文本评分重写的 Prompt
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
    client = OpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=settings.OPENROUTER_API_KEY,
    )
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
            response_format = {"type": "json_object"},  # 👈 关键！强制 JSON 输出
            temperature = 0,  # 👈 提高一致性
            timeout = 120  # 👈 防止无限等待
        )
        content = completion.choices[0].message.content
        logger.info(f"✅ AI 文本分析成功！返回内容: {content}")
        return content
    except Exception as e:  # 或更精确地捕获 openai.APIError 等
        logger.info(f"❌ 调用 OpenRouter API 失败: {e}")
        return None

def grade_submission_with_ai(standard_answer, total_score, assignment_status_id):
    """
    使用AI对作业提交进行评分
    参数:
        standard_answer: 标准答案
        total_score: 题目总分
        assignment_status_id: 作业状态ID
    返回:
        AI评分的JSON字符串
    """
    try:
        # 通过assignment_status_id获取作业状态和关联的提交记录
        assignment_status = AssignmentStatus.objects.get(id=assignment_status_id)
        submission = assignment_status.submission

        if not submission or not submission.submitted_image:
            return json.dumps({
                "score": 0,
                "justification": "错误：没有找到提交记录或图片"
            })

        # 获取图片路径
        image_path = submission.submitted_image.path

        # 这里调用您的OCR处理逻辑
        # extracted_text = extract_text_from_image(image_path)

        # 这里调用您的AI评分逻辑
        # 示例代码 - 替换为您的实际AI评分实现
        # ai_result = call_ai_grading_api(extracted_text, standard_answer, total_score)

        # 临时示例 - 返回一个模拟结果
        # 实际实现中，您需要调用您的AI服务
        import random
        score = round(random.uniform(0.5, 1.0) * total_score, 1)

        return json.dumps({
            "score": score,
            "justification": "AI评分完成"
        })

    except AssignmentStatus.DoesNotExist:
        logger.error(f"找不到ID为 {assignment_status_id} 的作业状态记录")
        return json.dumps({
            "score": 0,
            "justification": "错误：找不到作业状态记录"
        })
    except Exception as e:
        logger.error(f"AI评分过程中发生错误: {str(e)}")
        return json.dumps({
            "score": 0,
            "justification": f"评分错误: {str(e)}"
        })

@shared_task
def process_and_grade_submission(submission_id):
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        logger.info(f"❌ 找不到 ID 为 {submission_id} 的提交记录")
        return

    # 选择题逻辑保持不变
    if submission.problem.problem_type.name == "选择":
        # ... (这部分逻辑完全不变) ...
        logger.info('正在判选择题')
        student_choose = submission.choose_answer
        if not submission.problem.answer.content:
            submission.status = 'RUNTIME_ERROR'
            submission.justification = '错误：该题还未设置答案，无法批改。'
            submission.save()
            return
        if student_choose == submission.problem.answer.content:
            submission.status = 'ACCEPTED'
            submission.score = submission.problem.points
            submission.save()
            return
        else:
            submission.status = 'WRONG_ANSWER'
            submission.score = 0
            submission.justification = f'正确答案是 {submission.problem.answer.content}'
            submission.save()
            return

    logger.info('正在判大题 (纯 OCR + 文本 AI 方案)')
    # 1. 检查图片是否存在
    if not submission.submitted_image or not hasattr(submission.submitted_image, 'path'):
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：提交记录中没有图片文件或文件路径无效。'
        submission.save()
        return

    # 2. 调用OCR提取图片中的文本
    image_path = submission.submitted_image.path

    # 4. 调用 AI 进行评分 (不再需要 submission_id)
    problem = submission.problem
    ai_response_str = grade_submission_with_ai(
        standard_answer=problem.answer.explanation,
        total_score=problem.points,
        submission_id = submission_id,
    )

    # 5. 解析和保存结果
    if ai_response_str is None:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：调用AI评分接口失败。'
        submission.save()
        return

    try:
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        submission.status = 'Graded'
        submission.save()
        logger.info(f"✅ 提交 {submission_id} 评分完成！分数: {submission.score}")
    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = f'错误：解析AI返回结果失败。错误信息: {e}. AI原始返回: {ai_response_str}'
        submission.save()
        logger.info(f"❌ 解析AI结果失败: {e}")


@shared_task
def process_and_grade_submission(assignment_status_id):
    try:
        assignment_status = AssignmentStatus.objects.get(id=assignment_status_id)
    except AssignmentStatus.DoesNotExist:
        logger.info(f"❌ 找不到 ID 为 {assignment_status_id} 的作业状态记录")
        return

    # 获取关联的提交记录和题目
    submission = assignment_status.submission
    problem = assignment_status.assignment.problem

    if not problem:
        submission.status = 'RUNTIME_ERROR'
        assignment_status.save()
        submission.save()
        return

    # 选择题逻辑 - 使用文本匹配批改
    if problem.problem_type.name == "选择":
        logger.info('正在判选择题')
        student_choose = submission.choose_answer if submission else None

        if not problem.answer.content:
            submission.status= 'RUNTIME_ERROR'
            assignment_status.save()
            submission.save()
            return
        logger.info(f'正确答案是{problem.answer.content}，提交的答案是{student_choose}')
        if student_choose == problem.answer.content:
            submission.status = 'ACCEPTED'
            assignment_status.save()
            submission.save()
            logger.info(f"✅ 选择题批改完成 - 答案正确")
            return
        else:
            submission.status = 'WRONG_ANSWER'
            assignment_status.save()
            submission.save()
            # logger.info(submission.status)
            logger.info(f"✅ 选择题批改完成 - 答案错误")
            return

    # 填空和大题逻辑 - 都使用图片批改方法
    logger.info('正在判填空/大题 (使用图片批改方法)')

    # 检查是否有提交记录和图片
    if not submission or not submission.submitted_image or not hasattr(submission.submitted_image, 'path'):
        submission.status = 'RUNTIME_ERROR'
        assignment_status.save()
        submission.save()
        logger.error(f"❌ 提交记录中没有图片文件或文件路径无效")
        return

    # 调用 AI 进行图片批改
    ai_response_str = grade_submission_with_ai(
        standard_answer=problem.answer.explanation,
        total_score=problem.points,
        assignment_status_id=assignment_status_id,
    )

    # 解析和保存结果
    if ai_response_str is None:
        submission.status = 'RUNTIME_ERROR'
        assignment_status.save()
        submission.save()
        logger.error(f"❌ 调用AI评分接口失败")
        return

    try:
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        submission.status = 'GRADED'
        assignment_status.save()
        submission.save()
        logger.info(f"✅ 作业状态 {assignment_status_id} 图片批改完成！")
    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'RUNTIME_ERROR'
        assignment_status.save()
        submission.save()
        logger.error(f"❌ 解析AI结果失败: {e}")