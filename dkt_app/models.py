import torch
import torch.nn as nn


class DKTModel(nn.Module):
    def __init__(self, topic_size, emb_size=64):
        super(DKTModel, self).__init__()
        self.topic_size = topic_size
        self.emb_size = emb_size

        # 1. 引入 Embedding 层 (参考代码的精髓)
        # 将 (知识点索引 + 掌握情况) 映射到稠密向量空间
        # topic_size * 2 是因为每个知识点有“对”和“错”两种状态
        self.interaction_emb = nn.Embedding(topic_size * 2, emb_size)

        # 2. 使用多层 GRU 提高时序特征提取能力
        self.rnn = nn.GRU(emb_size, topic_size, num_layers=2, batch_first=True, dropout=0.2)

        # 3. 输出层与解耦
        self.dropout = nn.Dropout(0.4)
        self.score = nn.Linear(topic_size, topic_size)

        # 4. 初始化负偏置，让掌握度从 0 附近起步
        nn.init.constant_(self.score.bias, -3.0)

    def forward(self, q, r, h):
        """
        q: 知识点索引 (0 ~ topic_size-1)
        r: 回答情况 (0 或 1)
        h: 隐藏状态
        """
        if h is None:
            h = self.default_hidden()

        # --- 优化点：模拟遗忘衰减 ---
        # 在处理新练习前，先让旧记忆衰减 3%
        h = h * 0.999

        # 1. 计算当前所有知识点的掌握度 (用于预测和可视化)
        # 取 GRU 最后一层的隐藏状态 h[-1]
        all_logits = self.score(self.dropout(h[-1]))

        # 2. 提取当前练习题目的预测分 (用于 Loss)
        # 假设 q 是 one-hot 或 索引
        score_pred = torch.sum(all_logits * q.view(1, -1), dim=1)

        # 3. 构造交互输入 (参考标准 DKT 做法)
        # 将题目和表现合并为一个索引：如果做对，索引变为 q + topic_size
        # 这种做法比直接拼接向量更能学习到“错误”带来的深层信息
        interaction_idx = (q.argmax(dim=-1) + self.topic_size * r.long()).view(1, 1)
        x_emb = self.interaction_emb(interaction_idx)

        # 4. 更新隐状态
        _, h_next = self.rnn(x_emb, h)

        # 5. 平滑处理：防止曲线锯齿状跳变
        alpha = 0.5
        h_final = (1 - alpha) * h_next + alpha * h

        return score_pred, all_logits, h_final

    def default_hidden(self):
        # 维度：(层数, batch_size, hidden_size)
        return torch.zeros(2, 1, self.topic_size)


class DKT(nn.Module):
    def __init__(self, knowledge_n):
        super(DKT, self).__init__()
        self.seq_model = DKTModel(knowledge_n)

    def forward(self, topic, score, hidden=None):
        return self.seq_model(topic, score, hidden)