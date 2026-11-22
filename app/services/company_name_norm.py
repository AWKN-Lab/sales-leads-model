"""
企业名归一函数（独立模块 + 单元测试）。

规则（与工单要求逐字对应）：
  1. 全角转半角（NFKC）：全角括号（）→ ()、全角空格　→ 空格、中文标点 → 半角；
  2. 去空格：删除所有空白（含全角空格、Tab、换行）；
  3. 去掉常见后缀：股份有限公司 / 有限责任公司 / 集团公司 / 有限公司 / 集团 / 公司
     （**最长匹配优先**，且可重复剥离：「XX集团有限公司」→「XX集团」→「XX」）；
  4. 去掉首尾标点。

输入为 None 或空白时返回 ''（不抛异常，便于批量导入时逐行归一）。
"""

import re
import unicodedata

#: **法定形式**后缀（优先匹配；匹配到但剩余不足 2 字时**不再退到软后缀**）
LEGAL_SUFFIXES: tuple[str, ...] = (
    "股份有限公司",
    "有限责任公司",
    "集团公司",
    "有限公司",
)

#: **软**后缀（法定形式之后才考虑）
SOFT_SUFFIXES: tuple[str, ...] = ("集团", "公司")

#: 需要剥离的企业后缀（长后缀在前）
COMPANY_SUFFIXES: tuple[str, ...] = LEGAL_SUFFIXES + SOFT_SUFFIXES

#: 首尾要清掉的标点
_TRIM_CHARS = "，,。.、;；:：!！?？'\"“”‘’()（）[]【】-—_~"


def normalize_company_name(raw: str | None) -> str:
    """把企业名归一成用于匹配/去重的键。

    >>> normalize_company_name("北京某某（北京）  科技有限公司")
    '北京某某(北京)科技'
    >>> normalize_company_name("某某集团有限公司")
    '某某'
    """
    if raw is None:
        return ""
    text = unicodedata.normalize("NFKC", str(raw))
    # 2. 去所有空白
    text = re.sub(r"\s+", "", text)
    # 3. 去首尾标点（**先于**剥后缀：否则「有限公司、」这种带标点的名字剥不掉后缀）
    text = text.strip(_TRIM_CHARS)
    # 4. 剥离后缀（可重复；法定形式优先；剩余不足 2 字就不剥）
    changed = True
    while changed:
        changed = False
        for tier in (LEGAL_SUFFIXES, SOFT_SUFFIXES):
            for suffix in tier:
                if not text.endswith(suffix):
                    continue
                rest = text[: -len(suffix)]
                if len(rest) < 2:
                    # 剥完就没了（名字本身就是后缀）⇒ 停在法定形式这一层，不再退到软后缀
                    return text
                text = rest
                changed = True
                break
            if changed:
                break
    return text
