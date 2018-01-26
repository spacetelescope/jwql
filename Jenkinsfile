// Obtain files from source control system.
if (utils.scm_checkout()) return

/ Define each build configuration, copying and overriding values as necessary.
bc0 = new BuildConfig()
bc0.nodetype = "linux-stable"
bc0.build_mode = "debug"
bc0.build_cmds = ["conda install -q -y python=3.0",
                  "conda install -q -y astropy",
	       	  "python setup.py install"]
bco.test_cmds = ["conda install -q -y pytest",
	      	 "pytest"]
bc0.failedUnstableThresh = 1
bc0.failedFailureThresh = 1

 
 
bc1 = utils.copy(bc0)
bc1.build_cmds[0] = "conda install -q -y python=3.5"

/ Iterate over configurations that define the (distibuted) build matrix.
// Spawn a host of the given nodetype for each combination and run in parallel.
utils.concurrent([bc0, bc1])