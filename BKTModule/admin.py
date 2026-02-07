from django.contrib import admin
from .models import BKTKnowledgeModel, LearningTrace, BKTStudentState, BKTClassAnalytics, MigrationHistory

@admin.register(BKTKnowledgeModel)
class BKTKnowledgeModelAdmin(admin.ModelAdmin):
    list_display = ['knowledge_point', 'p_L0', 'p_T', 'p_G', 'p_S', 'training_samples', 'last_trained']
    list_filter = ['last_trained']
    search_fields = ['knowledge_point__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LearningTrace)
class LearningTraceAdmin(admin.ModelAdmin):
    list_display = ['student', 'knowledge_point', 'outcome', 'attempt_time', 'predicted_mastery_after']
    list_filter = ['outcome', 'attempt_time', 'knowledge_point']
    search_fields = ['student__username', 'knowledge_point__name']
    date_hierarchy = 'attempt_time'


@admin.register(BKTStudentState)
class BKTStudentStateAdmin(admin.ModelAdmin):
    list_display = ['student', 'knowledge_point', 'mastery_probability', 'total_attempts', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['student__username', 'knowledge_point__name']
    readonly_fields = ['last_updated']


@admin.register(BKTClassAnalytics)
class BKTClassAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['class_identifier', 'class_type', 'knowledge_point', 'student_count', 'average_mastery', 'calculated_at']
    list_filter = ['class_type', 'calculated_at']
    search_fields = ['class_identifier', 'knowledge_point__name']
    readonly_fields = ['calculated_at']


@admin.register(MigrationHistory)
class MigrationHistoryAdmin(admin.ModelAdmin):
    list_display = ['migration_type', 'description', 'status', 'started_at', 'completed_at', 'records_processed']
    list_filter = ['migration_type', 'status', 'started_at']
    search_fields = ['description', 'error_message']
    readonly_fields = ['started_at', 'completed_at', 'records_processed', 'error_message']
    date_hierarchy = 'started_at'
    
    def has_add_permission(self, request):
        # 不允许手动添加迁移记录
        return False
    
    def has_delete_permission(self, request, obj=None):
        # 只允许管理员删除
        return request.user.is_superuser