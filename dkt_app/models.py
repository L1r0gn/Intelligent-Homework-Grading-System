import torch
import torch.nn as nn
import torch.nn.functional as F

class DKTModel(nn.Module):
    def __init__(self, topic_size):
        super(DKTModel, self).__init__()
        self.topic_size = topic_size
        self.rnn = nn.GRU(topic_size * 2, topic_size, 1)
        # self.score = nn.Linear(topic_size * 2, 1)
        #changed
        self.score = nn.Linear(topic_size,topic_size)

    def forward(self, v, s, h):
        if h is None:
            h = self.default_hidden()
            
        v = v.type_as(h)

        # score = self.score(torch.cat([h.view(-1), v.view(-1)]))
        #
        # x = torch.cat([v.view(-1),
        #                (v * (s > 0.5).type_as(v).
        #                 expand_as(v).type_as(v)).view(-1)])
        # _, h = self.rnn(x.view(1, 1, -1), h)

        all_logits = self.score(h.view(1, -1))  # shape: [1, topic_size]

        # 2. 根据当前练习的题目 v，提取出对应知识点的预测分数（用于训练时的 Loss）
        # 使用题目向量 v 作为掩码，选取对应的 logit
        # 如果 v 是 one-hot，这里相当于取出了对应索引的预测值
        score = torch.sum(all_logits * v.view(1, -1), dim=1)

        # 3. 更新隐状态 (DKT 标准更新逻辑)
        # 表现向量：如果做对了，保留知识点特征；做错了，表现为 0
        performance = v * (s > 0.5).type_as(v)
        x = torch.cat([v.view(-1), performance.view(-1)])

        _, h = self.rnn(x.view(1, 1, -1), h)

        # 返回：当前题目的预测分数（供 train 计算 loss），所有知识点的掌握度 logits（供推理），以及更新后的 h
        return score, all_logits, h

        # return score.view(1), h

    def default_hidden(self):
        return torch.zeros(1, 1, self.topic_size)


class DKT(nn.Module):
    def __init__(self, knowledge_n):
        super(DKT, self).__init__()
        self.knowledge_n = knowledge_n
        self.seq_model = DKTModel(self.knowledge_n)
        
    def forward(self, topic, score, hidden=None):
        # s, hidden = self.seq_model(topic, score, hidden)
        # return s, hidden
        s, all_logits, hidden, = self.seq_model(topic, score, hidden)
        return s, all_logits, hidden
