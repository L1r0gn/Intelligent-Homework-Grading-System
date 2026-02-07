import math
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)


class BKTEngine:
    """
    BKT（贝叶斯知识追踪）核心算法引擎
    实现经典的BKT模型计算逻辑
    """
    
    def __init__(self, params: Dict[str, float]):
        """
        初始化BKT引擎
        
        Args:
            params: 包含BKT参数的字典
                - p_L0: 初始掌握概率
                - p_T: 学习转移概率
                - p_G: 猜测概率
                - p_S: 失误概率
                - decay_factor: 遗忘衰减因子（可选）
        """
        self.p_L0 = params.get('p_L0', 0.1)
        self.p_T = params.get('p_T', 0.3)
        self.p_G = params.get('p_G', 0.1)
        self.p_S = params.get('p_S', 0.1)
        self.decay_factor = params.get('decay_factor', 0.95)
        
        # 参数验证
        self._validate_parameters()
    
    def _validate_parameters(self):
        """验证BKT参数的有效性"""
        params = [self.p_L0, self.p_T, self.p_G, self.p_S, self.decay_factor]
        param_names = ['p_L0', 'p_T', 'p_G', 'p_S', 'decay_factor']
        
        for param, name in zip(params, param_names):
            if not 0 <= param <= 1:
                raise ValueError(f"参数 {name} 必须在 0-1 之间，当前值: {param}")
    
    def update_mastery_probability(self, current_prob: float, is_correct: bool) -> float:
        """
        根据答题结果更新掌握概率（BKT核心公式）
        
        Args:
            current_prob: 当前掌握概率 P(Lt)
            is_correct: 答题是否正确
            
        Returns:
            更新后的掌握概率 P(Lt+1)
        """
        try:
            # 应用遗忘衰减（如果设置了衰减因子且不是第一次答题）
            if current_prob > 0 and self.decay_factor < 1.0:
                current_prob *= self.decay_factor
            
            # BKT贝叶斯更新公式
            if is_correct:
                # 答对的情况
                numerator = current_prob * (1 - self.p_S) + (1 - current_prob) * self.p_G
                denominator = current_prob * (1 - self.p_S) + (1 - current_prob) * self.p_G
                
                if denominator == 0:
                    new_prob = current_prob + self.p_T * (1 - current_prob)
                else:
                    # P(L|correct) = P(correct|L) * P(L) / P(correct)
                    p_correct_given_mastered = 1 - self.p_S
                    p_correct_given_not_mastered = self.p_G
                    
                    p_mastered_and_correct = current_prob * p_correct_given_mastered
                    p_not_mastered_and_correct = (1 - current_prob) * p_correct_given_not_mastered
                    p_correct = p_mastered_and_correct + p_not_mastered_and_correct
                    
                    posterior = p_mastered_and_correct / p_correct if p_correct > 0 else current_prob
                    new_prob = posterior
            else:
                # 答错的情况
                numerator = current_prob * self.p_S + (1 - current_prob) * (1 - self.p_G)
                denominator = current_prob * self.p_S + (1 - current_prob) * (1 - self.p_G)
                
                if denominator == 0:
                    new_prob = current_prob
                else:
                    # P(L|incorrect) = P(incorrect|L) * P(L) / P(incorrect)
                    p_incorrect_given_mastered = self.p_S
                    p_incorrect_given_not_mastered = 1 - self.p_G
                    
                    p_mastered_and_incorrect = current_prob * p_incorrect_given_mastered
                    p_not_mastered_and_incorrect = (1 - current_prob) * p_incorrect_given_not_mastered
                    p_incorrect = p_mastered_and_incorrect + p_not_mastered_and_incorrect
                    
                    posterior = p_mastered_and_incorrect / p_incorrect if p_incorrect > 0 else current_prob
                    new_prob = posterior
            
            # 应用学习转移概率
            new_prob = new_prob + self.p_T * (1 - new_prob)
            
            # 确保概率在有效范围内
            new_prob = max(0.0, min(1.0, new_prob))
            
            logger.debug(f"BKT更新: {current_prob:.3f} -> {new_prob:.3f} (正确: {is_correct})")
            return new_prob
            
        except Exception as e:
            logger.error(f"BKT概率更新出错: {e}")
            return current_prob
    
    def predict_next_performance(self, mastery_prob: float) -> float:
        """
        预测下次答题的正确概率
        
        Args:
            mastery_prob: 当前掌握概率
            
        Returns:
            预测的正确概率
        """
        # P(correct) = P(L) * (1-P(S)) + (1-P(L)) * P(G)
        predicted_accuracy = mastery_prob * (1 - self.p_S) + (1 - mastery_prob) * self.p_G
        return max(0.0, min(1.0, predicted_accuracy))
    
    def simulate_learning_path(self, initial_prob: float, outcomes: list) -> list:
        """
        模拟学习路径
        
        Args:
            initial_prob: 初始掌握概率
            outcomes: 答题结果列表 (True/False)
            
        Returns:
            掌握概率变化序列
        """
        probabilities = [initial_prob]
        current_prob = initial_prob
        
        for outcome in outcomes:
            current_prob = self.update_mastery_probability(current_prob, outcome)
            probabilities.append(current_prob)
        
        return probabilities
    
    def estimate_parameters(self, response_sequences: list) -> Dict[str, float]:
        """
        基于答题序列估计BKT参数（简化版EM算法）
        注意：这是一个简化的实现，实际应用中建议使用专门的BKT参数估计算法
        
        Args:
            response_sequences: 答题序列列表，每个序列包含True/False
            
        Returns:
            估计的参数字典
        """
        if not response_sequences:
            return self.get_default_parameters()
        
        # 简单的启发式估计
        all_responses = []
        for seq in response_sequences:
            all_responses.extend(seq)
        
        if not all_responses:
            return self.get_default_parameters()
        
        correct_rate = sum(all_responses) / len(all_responses)
        
        # 基于正确率的简单估计
        estimated_params = {
            'p_L0': max(0.05, min(0.3, correct_rate * 0.3)),  # 初始掌握概率
            'p_T': max(0.1, min(0.5, correct_rate * 0.4)),   # 学习转移概率
            'p_G': max(0.05, min(0.3, (1 - correct_rate) * 0.3)),  # 猜测概率
            'p_S': max(0.05, min(0.3, (1 - correct_rate) * 0.2)),  # 失误概率
            'decay_factor': 0.95
        }
        
        return estimated_params
    
    def get_default_parameters(self) -> Dict[str, float]:
        """获取默认参数"""
        return {
            'p_L0': self.p_L0,
            'p_T': self.p_T,
            'p_G': self.p_G,
            'p_S': self.p_S,
            'decay_factor': self.decay_factor
        }
    
    def calculate_information_gain(self, current_prob: float, is_correct: bool) -> float:
        """
        计算本次答题的信息增益
        
        Args:
            current_prob: 答题前的掌握概率
            is_correct: 答题结果
            
        Returns:
            信息增益值
        """
        new_prob = self.update_mastery_probability(current_prob, is_correct)
        
        # 使用熵来衡量信息增益
        def entropy(p):
            if p <= 0 or p >= 1:
                return 0
            return -(p * math.log2(p) + (1-p) * math.log2(1-p))
        
        old_entropy = entropy(current_prob)
        new_entropy = entropy(new_prob)
        
        return old_entropy - new_entropy


class MultiSkillBKTEngine:
    """
    多知识点BKT引擎
    处理涉及多个知识点的题目
    """
    
    def __init__(self, skill_params: Dict[int, Dict[str, float]]):
        """
        初始化多技能BKT引擎
        
        Args:
            skill_params: {knowledge_point_id: bkt_params_dict}
        """
        self.skill_engines = {}
        for skill_id, params in skill_params.items():
            self.skill_engines[skill_id] = BKTEngine(params)
    
    def update_multiple_skills(self, skill_states: Dict[int, float], 
                             outcomes: Dict[int, bool]) -> Dict[int, float]:
        """
        同时更新多个知识点的掌握概率
        
        Args:
            skill_states: {skill_id: current_probability}
            outcomes: {skill_id: is_correct}
            
        Returns:
            更新后的状态字典
        """
        updated_states = skill_states.copy()
        
        for skill_id, is_correct in outcomes.items():
            if skill_id in self.skill_engines and skill_id in updated_states:
                engine = self.skill_engines[skill_id]
                updated_states[skill_id] = engine.update_mastery_probability(
                    updated_states[skill_id], is_correct
                )
        
        return updated_states