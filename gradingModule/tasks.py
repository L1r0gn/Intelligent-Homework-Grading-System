import json

import requests
from celery import shared_task
from .models import Submission, Problem
from IntelligentHomeworkGradingSystem import settings
import base64
# --- 步骤 1 & 2: OCR 功能 ---
# def extract_text_from_image(image_path):
#     """使用 Tesseract OCR 从图片中提取文本。"""
#     try:
#         image = Image.open(image_path)
#         text = pytesseract.image_to_string(image, lang='chi_sim+eng')
#         print("✅ OCR 识别成功！")
#         return text
#     except Exception as e:
#         print(f"❌ OCR 识别失败: {e}")
#         return None

def encode_image_to_base64(image_path):
    """将图片文件编码为 Base64 字符串。"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ 编码图片失败: {e}")
        return None


def grade_submission_with_ai(standard_answer, image_path, total_score):
    """使用 OpenRouter 的视觉模型进行分析和打分。"""

    # 1. 将图片编码为 Base64
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return None
    print('标准答案为',standard_answer)
    print()
    # 2. 更新 Prompt，告知 AI 直接分析图片
    prompt = f"""
    # 角色
    你是一名经验丰富、严格公正的阅卷老师。
    # 任务
    请根据提供的“标准答案”，对“学生提交的答案图片”进行分析和打分。
    # 上下文
    - 题目总分: {total_score}分
    - 标准答案: ```{standard_answer}```
    - 学生提交的答案在图片中，请仔细查看图片内容。
    # 评分要求
    1.  仔细分析图片中的学生作答内容，并与“标准答案”进行比对，识别出学生答对的关键得分点。
    2.  识别出学生遗漏的、或回答错误的地方。
    3.  综合分析，给出一个合理的分数。分数必须是整数。
    4.  用简洁的语言给出评分的理由。
    # 输出格式
    请严格按照以下 JSON 格式返回你的评分结果，不要包含任何额外的解释或文字。
    {{
      "score": <你给出的分数 (整数)>,
      "justification": "<你给出的评分理由 (字符串)>"
    }}
    """

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        # --- 更换为视觉模型 ---
        "model": "google/gemma-3-27b-it:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_path
                        }
                    }
                ]
            }
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data,timeout=360)
        response.raise_for_status()
        print("✅ AI 视觉分析成功！")
    except requests.RequestException as e:
        print(f"❌ 调用 OpenRouter Vision API 失败: {e}")
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
            submission.score = 0 # 答错应该是0分
            submission.justification = f'正确答案是 {submission.problem.answer.content}'
            submission.save()
            return

    print('正在判大题 (使用Vision API)')
    # 1. 检查图片是否存在
    if not submission.submitted_image or not hasattr(submission.submitted_image, 'path'):
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：提交记录中没有图片文件或文件路径无效。'
        submission.save()
        return

    # --- 移除 OCR 步骤 ---
    # image_path = submission.submitted_image.path
    # extracted_text = extract_text_from_image(image_path) ... (这些都删掉)

    # 2. 直接调用 AI 进行评分
    problem = submission.problem
    ai_response_str = grade_submission_with_ai(
        problem.answer.explanation, # 标准答案
        submission.submitted_image.path, # 直接传入图片路径
        problem.points
    )

    # ... (后续的解析和保存逻辑完全不变) ...
    if ai_response_str is None:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：调用AI评分接口失败。'
        submission.save()
        return

    try:
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        # 如果AI没有识别出文字，可以将submitted_text留空或填充提示信息
        submission.submitted_text = "[由Vision AI直接评分]"
        submission.status = 'Graded' # 你可以自定义一个状态，比如 'GRADED'
        submission.save()
        print(f"✅ 提交 {submission_id} 评分完成！")
    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'RUNTIME_ERROR' # 或者自定义一个 'AI_ERROR' 状态
        submission.justification = f'错误：解析AI返回结果失败。错误信息: {e}. AI原始返回: {ai_response_str}'
        submission.save()
        print(f"❌ 解析AI结果失败: {e}")