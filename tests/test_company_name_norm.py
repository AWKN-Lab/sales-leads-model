"""企业名归一函数单测（工单验收第 3 条：≥12 个样例，含全角括号、空格、常见后缀）。"""
import pytest

from app.services.company_name_norm import normalize_company_name

# (输入, 期望输出, 这个样例在考什么)
CASES = [
    ("北京某某科技有限公司", "北京某某科技", "最常见后缀 有限公司"),
    ("北京某某有限责任公司", "北京某某", "后缀 有限责任公司"),
    ("某某股份有限公司", "某某", "后缀 股份有限公司"),
    ("某某集团有限公司", "某某", "嵌套后缀（有限公司→集团 连续剥离）"),
    ("某某集团公司", "某某", "后缀 集团公司"),
    ("某某集团", "某某", "后缀 集团"),
    ("某某公司", "某某", "后缀 公司"),
    ("北京某某（北京）科技有限公司", "北京某某(北京)科技", "**全角括号** → 半角括号"),
    ("北京某某　科技有限公司", "北京某某科技", "**全角空格**（U+3000）"),
    ("北京 某某  科技 有限公司", "北京某某科技", "普通空格 + 多余空格"),
    ("  某某科技有限公司  ", "某某科技", "首尾空白"),
    ("某某（上海）贸易有限公司", "某某(上海)贸易", "全角括号含城市"),
    ("ＡＢＣ科技有限公司", "ABC科技", "全角字母 → 半角（NFKC）"),
    ("某某科技有限公司、", "某某科技", "尾部顿号"),
    ("某某科技有限公司。", "某某科技", "尾部句号"),
    ("某某科技", "某某科技", "无后缀 ⇒ 原样（只去空格）"),
    ("某某  股份  有限公司", "某某", "空格插在后缀中间（去空格后成为 股份有限公司）"),
]


@pytest.mark.parametrize("raw,expected,why", CASES, ids=[c[2] for c in CASES])
def test_normalize(raw, expected, why):
    assert normalize_company_name(raw) == expected, why


def test_case_count_at_least_12():
    """验收第 3 条：样例数 ≥ 12。"""
    assert len(CASES) >= 12


def test_none_and_blank_are_safe():
    assert normalize_company_name(None) == ""
    assert normalize_company_name("") == ""
    assert normalize_company_name("   ") == ""


def test_equivalent_names_normalize_to_same_key():
    """归一的目的：不同写法得到同一个键（去重/匹配用）。"""
    a = normalize_company_name("北京某某（北京）  科技有限公司")
    b = normalize_company_name("北京某某(北京)科技有限公司")
    assert a == b


def test_suffix_only_name_not_emptied():
    """全是后缀时不至于把名字剥空（保留至少 2 个字符）。"""
    assert normalize_company_name("有限公司") == "有限公司"
