"""
验证 CI/CD 集成

测试目标：
1. GitHub Actions 工作流配置正确性
2. 测试命令可执行性
3. 测试覆盖率统计
"""

import pytest
import os
import subprocess
import yaml


class TestCIConfiguration:
    """测试 CI 配置"""

    def test_workflow_file_exists(self):
        """测试：工作流文件存在"""
        workflow_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".github",
            "workflows",
            "evaluation.yml",
        )

        assert os.path.exists(workflow_path), f"Workflow file not found: {workflow_path}"

    def test_workflow_yaml_valid(self):
        """测试：YAML 语法有效"""
        workflow_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".github",
            "workflows",
            "evaluation.yml",
        )

        with open(workflow_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")

    def test_workflow_has_required_jobs(self):
        """测试：包含必要任务"""
        workflow_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".github",
            "workflows",
            "evaluation.yml",
        )

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        assert "jobs" in workflow
        assert "test" in workflow["jobs"]
        assert "lint" in workflow["jobs"]

    def test_workflow_triggers(self):
        """测试：触发器配置"""
        workflow_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".github",
            "workflows",
            "evaluation.yml",
        )

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        assert True in workflow or "on" in workflow
        triggers = workflow.get(True, workflow.get("on", {}))
        assert "push" in triggers
        assert "pull_request" in triggers
        assert "workflow_dispatch" in triggers


class TestTestCommands:
    """测试命令可执行性"""

    def test_pytest_available(self):
        """测试：pytest 可用"""
        result = subprocess.run(
            ["python", "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_metrics_tests_importable(self):
        """测试：指标测试可导入"""
        from test import test_stability_metric
        from test import test_latency_metric
        from test import test_toolcall_metric

        assert test_stability_metric is not None
        assert test_latency_metric is not None
        assert test_toolcall_metric is not None

    def test_benchmark_tests_importable(self):
        """测试：基准测试可导入"""
        from test import test_reviewer_benchmark
        from test import test_pipeline_benchmark

        assert test_reviewer_benchmark is not None
        assert test_pipeline_benchmark is not None

    def test_reporter_tests_importable(self):
        """测试：报告测试可导入"""
        from test import test_eval_md_reporter
        from test import test_eval_html_reporter

        assert test_eval_md_reporter is not None
        assert test_eval_html_reporter is not None


class TestEvaluationModule:
    """评测模块测试"""

    def test_evaluation_package_importable(self):
        """测试：评测包可导入"""
        import evaluation

        assert evaluation is not None

    def test_metrics_module_importable(self):
        """测试：指标模块可导入"""
        from evaluation import metrics

        assert metrics is not None

    def test_benchmark_module_importable(self):
        """测试：基准模块可导入"""
        from evaluation import benchmark

        assert benchmark is not None

    def test_datasets_module_importable(self):
        """测试：数据集模块可导入"""
        from evaluation import datasets

        assert datasets is not None

    def test_reporter_module_importable(self):
        """测试：报告模块可导入"""
        from evaluation import reporter

        assert reporter is not None


class TestTestDiscovery:
    """测试发现"""

    def test_discover_all_tests(self):
        """测试：发现所有测试"""
        result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )

        assert "test session starts" in result.stdout or result.returncode == 0

    def test_test_count(self):
        """测试：测试数量"""
        test_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "test",
        )

        test_files = [
            f
            for f in os.listdir(test_dir)
            if f.startswith("test_") and f.endswith(".py")
        ]

        assert len(test_files) >= 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
