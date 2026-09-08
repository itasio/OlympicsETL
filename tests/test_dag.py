import unittest
from pathlib import Path


try:
    from airflow.models import DagBag
except ModuleNotFoundError:
    DagBag = None


@unittest.skipIf(DagBag is None, "Airflow is provided by the Docker image")
class DagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dag_folder = Path(__file__).resolve().parents[1] / "dags"
        cls.dag_bag = DagBag(dag_folder=str(dag_folder), include_examples=False)

    def test_dag_imports_without_errors(self):
        self.assertEqual({}, self.dag_bag.import_errors)

    def test_dag_has_expected_tasks_and_dependency(self):
        dag = self.dag_bag.dags.get("olympics_etl")

        self.assertIsNotNone(dag)
        self.assertFalse(dag.catchup)
        self.assertIsNone(dag.schedule_interval)
        self.assertEqual(1, dag.max_active_runs)
        self.assertEqual(
            {
                "load_olympics_data",
                "validate_loaded_data",
                "query_olympics_data",
            },
            set(dag.task_ids),
        )
        self.assertEqual(
            {"validate_loaded_data"},
            dag.get_task("load_olympics_data").downstream_task_ids,
        )
        self.assertEqual(
            {"query_olympics_data"},
            dag.get_task("validate_loaded_data").downstream_task_ids,
        )


if __name__ == "__main__":
    unittest.main()
