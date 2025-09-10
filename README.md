This is a CNV pipeline for calling from exome data.

Suggested usage:

1. Install dependencies from github (this pipeline, vr-runner)


2. xxxxxxxxxxxxxxxxxxxxx

# Three CNV callers
run-clamms +config run-clamms.conf -o out.clamms -b ref/bam-sample-sex.txt
run-xhmm   +config run-xhmm.conf   -o out.xhmm   -b ref/bam-sex.txt
run-exomedepth +config run-exomedepth.conf -o out.exomedepth -b ref/bam-sample-sex.txt


# CoNVex we only use normalized depth profiles from CoNVex to get an unbiased estimator
run-convex +config run-convex.conf -o out.convex -b ref/bam-sex.txt


# Consolidate the calls
run-consolidate-cnvs +config run-consolidate-cnvs.conf -o out.consolidate

