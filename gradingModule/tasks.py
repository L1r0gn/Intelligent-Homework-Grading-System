import json
import requests
from celery import shared_task
from openai import OpenAI

from .models import Submission, Problem
from IntelligentHomeworkGradingSystem import settings
import base64
from PIL import Image
import pytesseract

def encode_image_to_base64(image_path):
    """将图片文件编码为 Base64 字符串。"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ 编码图片失败: {e}")
        return None


def grade_submission_with_ai(standard_answer, total_score, student_answer_text,submission_id):
    """使用的语言模型对OCR文本进行分析和打分。"""
    print('标准答案为', standard_answer)
    image_url = f"http://119.29.152.140//grading/submission-image/{submission_id}"
    print(image_url)
    # 针对纯文本评分重写的 Prompt
    prompt = f"""
    # 角色
    你是一名经验丰富、严格公正的阅卷老师。
    # 任务
    请根据提供的“标准答案”，对“学生提交的答案图片”进行分析和打分。
    # 上下文
    - 题目总分: {total_score}分
    - 标准答案: ```{standard_answer}```
    - 学生提交的答案文本 (来自OCR): ```{student_answer_text}```
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
                        {"image": image_url},
                        {"text":prompt}
                    ]
                }
            ],
            response_format = {"type": "json_object"},  # 👈 关键！强制 JSON 输出
            temperature = 0,  # 👈 提高一致性
            timeout = 120  # 👈 防止无限等待
        )
        content = completion.choices[0].message.content
        print(f"✅ AI 文本分析成功！返回内容: {content}")
        return content
    except Exception as e:  # 或更精确地捕获 openai.APIError 等
        print(f"❌ 调用 OpenRouter API 失败: {e}")
        return None
@shared_task
def process_and_grade_submission(submission_id):
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        print(f"❌ 找不到 ID 为 {submission_id} 的提交记录")
        return

    # 选择题逻辑保持不变
    if submission.problem.problem_type.name == "选择":
        # ... (这部分逻辑完全不变) ...
        print('正在判选择题')
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

    print('正在判大题 (纯 OCR + 文本 AI 方案)')
    # 1. 检查图片是否存在
    if not submission.submitted_image or not hasattr(submission.submitted_image, 'path'):
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：提交记录中没有图片文件或文件路径无效。'
        submission.save()
        return

    # 2. 调用OCR提取图片中的文本
    image_path = submission.submitted_image.path
    extracted_text = extract_text_from_image(image_path)

    # 3. 检查OCR结果，如果为空则无法评分
    if not extracted_text or not extracted_text.strip():
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：OCR未能从图片中识别出任何有效文本，无法进行评分。'
        submission.submitted_text = "OCR识别失败或为空。"
        submission.save()
        print(f"❌ 提交 {submission_id} 的图片OCR识别失败或为空。")
        return

    # 4. 调用 AI 进行评分 (不再需要 submission_id)
    problem = submission.problem
    ai_response_str = grade_submission_with_ai(
        standard_answer=problem.answer.explanation,
        total_score=problem.points,
        student_answer_text=extracted_text,  # 传入OCR识别的文本
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
        submission.submitted_text = extracted_text
        submission.status = 'Graded'
        submission.save()
        print(f"✅ 提交 {submission_id} 评分完成！分数: {submission.score}")
    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = f'错误：解析AI返回结果失败。错误信息: {e}. AI原始返回: {ai_response_str}'
        submission.save()
        print(f"❌ 解析AI结果失败: {e}")