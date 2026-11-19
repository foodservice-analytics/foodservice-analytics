"""Independent numerical validation of the server Cox solver on a tied synthetic cohort."""
import importlib.util,unittest,math
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
from pathlib import Path
spec=importlib.util.spec_from_file_location('worker',Path('src/server_pipeline/workers/cox_worker.py'));worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
class CoxTests(unittest.TestCase):
 def test_coefficients_match_independent_scipy_optimizer(self):
  rng=np.random.default_rng(811);n=100;chain=rng.integers(0,2,n);comp=rng.integers(0,20,n);dur=rng.integers(1,80,n);events=rng.integers(0,2,n)
  rows=[{'category':'Кафе','district':'Центральный район','ownership':'chain' if chain[i] else 'independent','competitors_300m':int(comp[i]),'duration':int(dur[i]),'event':int(events[i])} for i in range(n)]
  actual=worker.fit(rows);beta=np.array([r['coef'] for r in actual]);x=np.column_stack([chain,comp/10.,np.zeros(n)])
  def objective(b):
   eta=x@b;ll=0.
   for t in np.unique(dur[events==1]):
    selected=(dur==t)&(events==1);ll+=eta[selected].sum()-selected.sum()*logsumexp(eta[dur>=t])
   return -ll+.5*np.dot(b,b)
  reference=minimize(objective,np.zeros(3),method='BFGS',tol=1e-8)
  self.assertLess(np.max(np.abs(beta-reference.x)),1e-5)
  self.assertTrue(all(r['ci_low']<=r['hazard_ratio']<=r['ci_high'] for r in actual))
if __name__=='__main__':unittest.main()
