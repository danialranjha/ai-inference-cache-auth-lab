"""Run baseline tests and two functional mutants using the same assertions."""
import io
import json
from pathlib import Path
import unittest
import experiment


def suite_result():
    suite=unittest.defaultTestLoader.discover('tests')
    result=unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'failed_tests':[test.id() for test,_ in result.failures], 'success':result.wasSuccessful()}


def main():
    baseline=suite_result()
    assert baseline['tests']==11 and baseline['success'],baseline
    original=experiment.run_all
    mutants={}
    try:
        for name in ('bypass','deny_all'):
            async def mutated(mutation=None, name=name):
                return await original(name)
            experiment.run_all=mutated
            result=suite_result()
            assert not result['success'] and result['failures'] and not result['errors'],result
            mutants[name]=result
    finally:
        experiment.run_all=original
    report={'baseline':baseline,'mutants':mutants}
    Path('artifacts/checks.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
