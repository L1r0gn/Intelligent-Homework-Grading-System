import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from questionManageModule.models import Problem, ProblemContent, Answer  # 替换为你的实际应用名
from questionManageModule.views import handle_problem_creation  # 导入核心处理函数

User = get_user_model()

class Command(BaseCommand):
    help = '从JSON文件导入问题到数据库'

    def add_arguments(self, parser):
        # 接收JSON文件路径参数
        parser.add_argument('json_file', type=str, help='JSON数据集文件的路径')
        # 可选参数：指定创建人ID（默认为第一个超级用户）
        parser.add_argument('--creator', type=str, help='创建人用户ID', default=None)

    def handle(self, *args, **options):
        json_path = options['json_file']
        creator_id = options['creator']

        # 获取创建人（默认为第一个超级用户）
        try:
            if creator_id:
                creator = User.objects.get(username=creator_id)
            else:
                creator = User.objects.filter(is_superuser=True).first()
                if not creator:
                    self.stdout.write(self.style.ERROR('未找到超级用户，请指定--creator参数'))
                    return
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'用户ID {creator_id} 不存在'))
            return

        # 读取JSON文件
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                self.stdout.write(self.style.ERROR('JSON必须是数组格式'))
                return
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'文件 {json_path} 不存在'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('JSON格式错误'))
            return

        # 批量导入
        success = 0
        fail = 0
        for idx, item in enumerate(data, 1):
            try:
                handle_problem_creation(
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    difficulty=item.get('difficulty', 2),
                    problem_type=item.get('problem_type',1),
                    subject=item.get('subject'),
                    estimated_time=item.get('estimated_time', 10),
                    content_data=item.get('content_data', '{}'),
                    creator=creator,
                    points=item.get('points', 0),
                    answer_data=item.get('answer')
                )
                success += 1
                self.stdout.write(f'第{idx}条导入成功')
            except Exception as e:
                fail += 1
                self.stdout.write(self.style.ERROR(f'第{idx}条导入失败：{str(e)}'))

        # 输出结果
        self.stdout.write('\n' + self.style.SUCCESS(f'导入完成：成功{success}条，失败{fail}条'))