from django.test import TestCase

from functional_test.case_no import assign_unique_case_nos, requirement_initials
from functional_test.testcase_parser import parse_test_cases

SAMPLE_MARKDOWN = '''
根据提供的需求文档和历史测试用例信息，以下为《长银需求--B端投保》功能测试用例的生成：

### 测试用例编号：TC_01
**标题**：授信申请功能测试
**前置条件**：
- 系统正常运行。
- 用户已注册并登录。
**步骤**：
1. 用户登录系统。
2. 用户进入授信申请页面。
**预期结果**：
- 系统显示授信申请提交成功。
**优先级**：高

### 测试用例编号：TC_02
**标题**：授信状态查询功能测试
**前置条件**：
- 系统正常运行。
**步骤**：
1. 用户登录系统。
2. 用户点击查询按钮。
**预期结果**：
- 系统显示授信申请的当前状态。
**优先级**：高
'''


class TestCaseParserTests(TestCase):
    def test_parse_tc_underscore_format(self):
        cases = parse_test_cases(SAMPLE_MARKDOWN)
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]['case_no'], 'TC-01')
        self.assertEqual(cases[0]['title'], '授信申请功能测试')
        self.assertIn('系统正常运行', cases[0]['precondition'])
        self.assertIn('用户登录系统', cases[0]['steps'])
        self.assertIn('提交成功', cases[0]['expected_result'])
        self.assertEqual(cases[0]['priority'], '高')
        self.assertEqual(cases[1]['case_no'], 'TC-02')

    def test_parse_fallback_single_case(self):
        cases = parse_test_cases('这是一段未结构化输出')
        self.assertEqual(cases, [])

    def test_parse_structured_markdown(self):
        markdown = '''
### TC-001 用户登录成功
**标题：** 用户登录成功
**前置条件：** 用户已注册
**测试步骤：**
1. 打开登录页
2. 输入账号密码
**预期结果：** 登录成功进入首页
**优先级：** P0

### TC-002 密码错误
**标题：** 密码错误提示
**前置条件：** 用户已注册
**测试步骤：** 输入错误密码
**预期结果：** 提示密码错误
**优先级：** P1
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]['case_no'], 'TC-01')
        self.assertEqual(cases[0]['title'], '用户登录成功')
        self.assertIn('打开登录页', cases[0]['steps'])
        self.assertEqual(cases[0]['expected_result'], '登录成功进入首页')

    def test_parse_markdown_table(self):
        markdown = '''
# 长银需求--B端投保 功能测试用例
## 一、业务测试用例
| 编号 | 标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| TC-B-001 | 前筛规则按顺序执行 | 系统可用 | 1.发起前筛<br>2.命中拒绝 | 路由下一家资方 | 高 |
| TC-B-002 | 限制地区以同程侧配置为准 | 已配置限制地区 | 选择限制地区进件 | 被拒绝 | 中 |
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[0]['case_no'], 'TC-B-001')
        self.assertEqual(cases[0]['title'], '前筛规则按顺序执行')
        self.assertIn('发起前筛', cases[0]['steps'])
        self.assertIn('路由下一家资方', cases[0]['expected_result'])
        self.assertEqual(cases[0]['priority'], '高')
        self.assertEqual(cases[1]['case_no'], 'TC-B-002')
        self.assertEqual(cases[1]['title'], '限制地区以同程侧配置为准')

    def test_parse_module_and_priority(self):
        markdown = '''
### 测试用例编号：TC-用户登录-01
**模块**：用户登录
**标题**：输入正确手机号和验证码，验证登录成功
**前置条件**：用户已注册
**步骤**：
步骤1：输入手机号：13800138000
步骤2：输入正确验证码并点击登录
**预期结果**：页面跳转至首页，登录状态为在线
**优先级**：P0
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['case_no'], 'TC-用户登录-01')
        self.assertEqual(cases[0]['module'], '用户登录')
        self.assertEqual(cases[0]['priority'], 'P0')
        self.assertIn('13800138000', cases[0]['steps'])

    def test_requirement_initials_and_unique_case_no(self):
        self.assertEqual(requirement_initials('用户登录'), 'YHDL')
        self.assertEqual(requirement_initials('长银需求--B端投保.docx'), 'CYXQBDTB')
        cases = [
            {'case_no': 'TC-01', 'title': 'a'},
            {'case_no': 'TC-01', 'title': 'b'},
        ]
        assigned = assign_unique_case_nos(cases, '用户登录', ['TC-YHDL-001'])
        self.assertEqual(assigned[0]['case_no'], 'TC-YHDL-002')
        self.assertEqual(assigned[1]['case_no'], 'TC-YHDL-003')
        self.assertEqual(len({item['case_no'] for item in assigned}), 2)

    def test_infer_module_ignores_requirement_prefix(self):
        markdown = '''
### 测试用例编号：TC-YHDL-001
**模块**：用户登录
**标题**：登录成功
**前置条件**：无
**步骤**：打开登录页
**预期结果**：进入首页
**优先级**：P0
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(cases[0]['module'], '用户登录')

    def test_parse_plain_module_and_heading_fallback(self):
        markdown = '''
## 模块：进件前筛
### 测试用例编号：TC-CYXQ-001
模块名称：进件前筛
**标题**：命中拒绝规则后路由下一家
**前置条件**：无
**步骤**：发起前筛
**预期结果**：路由成功
**优先级**：P0

### 测试用例编号：TC-CYXQ-002
**标题**：限制地区拒绝
**前置条件**：无
**步骤**：选择限制地区
**预期结果**：被拒绝
**优先级**：P1
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(cases[0]['module'], '进件前筛')
        self.assertEqual(cases[1]['module'], '进件前筛')

    def test_drop_truncated_incomplete_cases(self):
        markdown = '''
| 编号 | 标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| TC-90 | 验证Safari浏览器下注册登录功能正常 | 已安装Safari | 1.执行注册<br>2.执行登录 | 功能正常 | P1 |
| TC-91 | 验证移动端浏览器下注册登录功能正常 | 已准备移动端 | 1. 在移动端执行完整注册流程<br>2
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['title'], '验证Safari浏览器下注册登录功能正常')
        self.assertEqual(cases[0]['priority'], 'P1')

        heading = '''
### 测试用例编号：TC-001
**标题**：完整用例
**前置条件**：无
**步骤**：打开登录页
**预期结果**：进入首页
**优先级**：P0

### 测试用例编号：TC-002
**标题**：被截断的用例
**前置条件**：无
**步骤**：
1. 在移动端执行完整注册流程
2
'''
        heading_cases = parse_test_cases(heading)
        self.assertEqual(len(heading_cases), 1)
        self.assertEqual(heading_cases[0]['title'], '完整用例')

    def test_table_module_from_section_and_pipeline(self):
        from functional_test.testcase_parser import apply_pipeline_modules

        markdown = '''
### 3. 兼容性
| 编号 | 标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| TC-90 | 验证Safari浏览器下注册登录功能正常 | 已安装Safari | 1.执行注册 | 功能正常 | P1 |
'''
        cases = parse_test_cases(markdown)
        self.assertEqual(cases[0]['module'], '兼容性')

        numbered = '''
### 1.1 前筛规则-多资方路由
| 编号 | 标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| TC-B-001 | 验证命中任一前筛规则拒绝后正确路由至下一资方 | 系统可用 | 1.发起前筛 | 路由下一家 | P0 |
'''
        numbered_cases = parse_test_cases(numbered)
        self.assertEqual(numbered_cases[0]['module'], '前筛规则-多资方路由')

        filled = apply_pipeline_modules(
            [{'title': '验证验证码发送成功', 'steps': '点击获取验证码', 'module': ''}],
            [{'模块': '用户注册', '功能点': '验证码发送'}],
        )
        self.assertEqual(filled[0]['module'], '用户注册')


