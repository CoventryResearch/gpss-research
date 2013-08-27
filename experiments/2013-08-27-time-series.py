Experiment(description='Trying tanh',
           data_dir='../data/tsdlr/',
           max_depth=10, 
           random_order=True,
           k=1,
           debug=False, 
           local_computation=False, 
           n_rand=9,
           sd=4, 
           max_jobs=400, 
           verbose=False,
           make_predictions=False,
           skip_complete=True,
           results_dir='../results/2013-08-27-time-series/',
           iters=150,
           base_kernels='StepTanh,BurstTanhSE,Per,Cos,Lin,SE,Const',
           zero_mean=True,
           random_seed=0,
           period_heuristic=5)