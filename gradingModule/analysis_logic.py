import logging

# 引入相关模型
# 注意：确保你的 questionManageModule/models.py 里已经定义了 StudentMastery 和 KnowledgePoint
from questionManageModule.models import StudentMastery
from gradingModule.models import Submission

logger = logging.getLogger(__name__)

class MasteryService:
    @staticmethod
    def calculate_mastery(student_id, knowledge_point_id):
        """
        核心算法：根据 Submission 计算特定知识点的掌握度
        """
        # 1. 查询该学生、在该知识点下、所有状态为'已批改'或'答案正确'的提交记录
        # 我们查找关联了该知识点的题目(problem__knowledge_points__id=knowledge_point_id)
        submissions = Submission.objects.filter(
            student_id=student_id,
            problem__knowledge_points__id=knowledge_point_id,
            status__in=['GRADED', 'ACCEPTED', 'WRONG_ANSWER']  # 包含错题，否则分母不准
        ).distinct()

        if not submissions.exists():
            return 0.0

        # 2. 统计总得分和总分值
        total_gained_score = 0
        total_possible_score = 0

        for sub in submissions:
            # 容错处理：防止题目被删或分数为None
            if sub.score is None or sub.problem is None:
                continue

            total_gained_score += sub.score
            # 使用题目定义的总分，如果未定义默认为10（需注意避免除以0）
            problem_points = sub.problem.points if sub.problem.points else 10
            total_possible_score += problem_points

        if total_possible_score == 0:
            return 0.0

        # 3. 计算百分比
        ratio = total_gained_score / total_possible_score

        # 4. 映射到 1-5 分制
        # 算法：百分比 * 5，保留一位小数
        # 示例：80% 正确率 -> 0.8 * 5 = 4.0 分
        score = round(ratio * 5, 1)

        # 修正：如果做过题但分数为0，最低给 1.0 分（鼓励分），或者保持 0.0 代表完全不懂
        # 这里假设只要做过题，最低 1.0
        if score < 1.0 and total_possible_score > 0:
            score = 1.0

        # 5. 更新或创建 StudentMastery 记录
        # 使用 update_or_create 也可以，这里用 get_or_create + save
        mastery, created = StudentMastery.objects.get_or_create(
            student_id=student_id,
            knowledge_point_id=knowledge_point_id
        )
        mastery.mastery_level = score
        mastery.total_questions_attempted = submissions.count()
        mastery.save()

        logger.info(f"📊 更新能力值: 学生{student_id} - 知识点{knowledge_point_id} - 新分数:{score}")
        return score

    @staticmethod
    def update_mastery_after_grading(submission_instance):
        """
        触发器：当 AI 批改完某个 Submission 后调用此方法
        """
        try:
            if not submission_instance.problem:
                return

            # 获取该题目关联的所有知识点
            # 注意：你需要先在 Problem 模型中添加 knowledge_points 字段
            related_kps = submission_instance.problem.knowledge_points.all()
            logger.info(f"获取到该submission的知识点：{related_kps}")

            if not related_kps.exists():
                logger.info(f"ℹ️ 题目 {submission_instance.problem.id} 未关联知识点，跳过能力值更新。")
                return

            for kp in related_kps:
                MasteryService.calculate_mastery(submission_instance.student.id, kp.id)

        except Exception as e:
            logger.error(f"❌ 更新能力值失败: {str(e)}")