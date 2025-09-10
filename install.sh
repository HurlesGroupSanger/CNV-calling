#!/usr/bin/env bash
#
# Author: petr.danecek@sanger
#
# List or install all prerequisities
#
# Usage:
#   ./install.sh DIR
#
# Example:
#   wget -qO- https://raw.githubusercontent.com/HurlesGroupSanger/cnv-calling/refs/heads/main/install.sh | bash -s dir
#

if [ $# != 1 ]; then
    echo "Usage:"
    echo "  ./install.sh DIR"
    echo
    exit;
fi

dst_dir=`realpath $1`
mkdir -p $dst_dir

download_main=0
script=$0
if [ $script != "bash" ]; then
    dir=`dirname $script`
    if [ "$dir" = ""  ]; then dir="."; fi
    dir=`realpath $dir`
    has_main=`cat $dir/.git/config | grep CNV-calling.git`
    if [ "$has_main" = "" ]; then
        download_main=1;
        echo 'export PATH='$dst_dir'/CNV-calling/src:$PATH' > $dst_dir/setenv.sh
    else
        echo 'export PATH='$dir'/src:$PATH' > $dst_dir/setenv.sh
    fi
else
    download_main=1
    echo 'export PATH='$dst_dir'/CNV-calling/src:$PATH' > $dst_dir/setenv.sh
fi

echo "pushd $dst_dir"
pushd $dst_dir

# Download the components:
# - this CNV-calling pipeline
set -e
if [ $download_main = "1" ] && [ ! -e "CNV-calling" ]; then
    git clone git@github.com:HurlesGroupSanger/CNV-calling.git
fi
set +e

# - vr-runner pipeline
perl -MRunner -e1 2>/dev/null
if [ "$?" != "0" ]; then
    if [ ! -e vr-runner/modules ]; then
        git clone git@github.com:VertebrateResequencing/vr-runner.git
    fi
    echo 'export PATH='$dst_dir'/vr-runner/scripts:$PATH' >> $dst_dir/setenv.sh
    echo 'export PERL5LIB='$dst_dir'/vr-runner/modules:$PERL5LIB' >> $dst_dir/setenv.sh
fi

# - run-convex pipeline
run-convex +sampleconf 2>/dev/null
if [ "$?" != "111" ]; then
    if [ ! -e CoNVex/utils/run-convex ]; then
        git clone git@github.com:HurlesGroupSanger/CoNVex.git
    fi
    echo 'export PATH='$dst_dir'/CoNVex/utils:$PATH' >> $dst_dir/setenv.sh
fi

# - samtools, annot-tsv
version=1.22
samtools  --version >/dev/null 2>&1; has_samtools=$(( $? != 0 ))
annot-tsv --version >/dev/null 2>&1; has_annot_tsv=$(( $? != 0 ))
if [ "$has_samtools" -ne 0 ] || [ "$has_annot_tsv" -ne 0 ]; then
    if [ ! -e samtools-$version/samtools ]; then
        echo "need samtools"
        wget https://github.com/samtools/samtools/releases/download/$version/samtools-$version.tar.bz2
        tar xjf samtools-$version.tar.bz2
        pushd samtools-$version
        set -e
        cd htslib-$version
        ./configure && make -j
        cd ..
        ./configure && make -j
        set +e
        popd
    fi
    echo 'export PATH='$dst_dir'/samtools-'$version':$PATH' >> $dst_dir/setenv.sh
    echo 'export PATH='$dst_dir'/samtools-'$version'/htslib-'$version':$PATH' >> $dst_dir/setenv.sh
fi


