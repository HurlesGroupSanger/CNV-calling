This is a CNV pipeline for calling from exome data.

Suggested usage:

1. Install dependencies (this pipeline, vr-runner, CoNVex, samtools, annot-tsv), e.g. with
   ```
   wget -qO- \
   https://raw.githubusercontent.com/HurlesGroupSanger/cnv-calling/refs/heads/main/install.sh | bash -s install_dir
   
   # set the paths: either add to your profile or execute before running the pipelines below
   . install_dir/setenv.sh
   ```

2. Run the CNV callers
   ```
   # Create a config file, edit it, then run the pipeline
   run-clamms +sampleconf > run-clamms.conf
   # edit run-clamms.conf
   run-clamms +config run-clamms.conf -o out.clamms -b ref/bam-sample-sex.txt

   run-xhmm +sampleconf > run-xhmm.conf
   # edit run-xhmm.conf
   run-xhmm   +config run-xhmm.conf   -o out.xhmm   -b ref/bam-sex.txt

   run-exomedepth +sampleconfig > run-exomedepth.conf
   # edit run-exomedepth.conf
   run-exomedepth +config run-exomedepth.conf -o out.exomedepth -b ref/bam-sample-sex.txt

   run-convex +sampleconf > run-convex.conf
   # edit run-convex +config run-convex.conf
   run-convex +config run-convex.conf -o out.convex -b ref/bam-sex.txt
   ```
