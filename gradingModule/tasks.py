import json
import requests
import pytesseract
from PIL import Image
from celery import shared_task
from django.conf import settings
from .models import Submission, Problem

# --- 步骤 1 & 2: OCR 功能 ---
def extract_text_from_image(image_path):
    """使用 Tesseract OCR 从图片中提取文本。"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        print("✅ OCR 识别成功！")
        return text
    except Exception as e:
        print(f"❌ OCR 识别失败: {e}")
        return None

# --- 步骤 3: AI 分析与打分功能 ---
def grade_submission_with_ai(standard_answer, student_submission, total_score):
    """使用 OpenRouter AI 进行分析和打分。"""
    prompt = f"""
    # 角色
    你是一名经验丰富、严格公正的阅卷老师。
    # 任务
    请根据提供的标准答案，对学生的提交内容进行分析和打分。
    # 上下文
    - 题目总分: {total_score}分
    - 标准答案: ```{standard_answer}```
    - 学生提交的内容 (来自OCR识别): ```{student_submission}```
    # 评分要求
    1.  仔细比对“学生提交的内容”和“标准答案”，识别出学生答对的关键得分点。
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
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response.raise_for_status()
        print("✅ AI 分析成功！")
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        print(f"❌ 调用 OpenRouter API 失败: {e}")
        return None

# --- 核心异步任务 ---
@shared_task
def     process_and_grade_submission(submission_id):
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        print(f"❌ 找不到 ID 为 {submission_id} 的提交记录")
        return

    print(submission.problem.problem_type)
    #选择题逻辑
    if submission.problem.problem_type.name == "选择":
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
            submission.score = submission.problem.points
            submission.save()
            return

    print('正在判大题')
    # 1. 从图片中提取文本
    if not submission.submitted_image:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：提交记录中没有图片文件。'
        submission.save()
        return

    image_path = submission.submitted_image.path
    extracted_text = extract_text_from_image(image_path)

    if extracted_text is None:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：OCR 图片识别失败。'
        submission.save()
        return

    # 将识别的文本存回数据库
    submission.submitted_text = extracted_text
    submission.save()

    # 2. 调用 AI 进行评分
    problem = submission.problem
    ai_response_str = grade_submission_with_ai(
        problem.answer,
        extracted_text,
        problem.points
    )

    if ai_response_str is None:
        submission.status = 'RUNTIME_ERROR'
        submission.justification = '错误：调用AI评分接口失败。'
        submission.save()
        return

    # 3. 解析AI返回结果并更新数据库
    try:
        # AI 返回的可能是字符串格式的 JSON，需要解析
        ai_result = json.loads(ai_response_str)
        submission.score = ai_result.get('score')
        submission.justification = ai_result.get('justification')
        submission.status = 'Graded'
        submission.save()
        print(f"✅ 提交 {submission_id} 评分完成！")
    except (json.JSONDecodeError, KeyError) as e:
        submission.status = 'Error'
        submission.justification = f'错误：解析AI返回结果失败。错误信息: {e}. AI原始返回: {ai_response_str}'
        submission.save()
        print(f"❌ 解析AI结果失败: {e}")