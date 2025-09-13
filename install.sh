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
    git clone --depth 1 git@github.com:HurlesGroupSanger/CNV-calling.git
fi
set +e

# - vr-runner pipeline
perl -MRunner -e1 2>/dev/null
if [ "$?" != "0" ]; then
    if [ ! -e vr-runner/modules ]; then
        git clone --depth 1 git@github.com:VertebrateResequencing/vr-runner.git
    fi
    echo 'export PATH='$dst_dir'/vr-runner/scripts:$PATH' >> $dst_dir/setenv.sh
    echo 'export PERL5LIB='$dst_dir'/vr-runner/modules:$PERL5LIB' >> $dst_dir/setenv.sh
fi

# - run-convex pipeline
run-convex +sampleconf 2>/dev/null
if [ "$?" != "111" ]; then
    if [ ! -e CoNVex/utils/run-convex ]; then
        git clone --depth 1 git@github.com:HurlesGroupSanger/CoNVex.git
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

# - clamms
: "${CLAMMS_DIR:=clamms}"
$CLAMMS_DIR/call_cnv >/dev/null 2>&1
if [ "$?" != "1" ]; then
    if [ ! -e $CLAMMS_DIR/call_cnv ]; then
        git clone --depth 1 https://github.com/rgcgithub/clamms.git clamms.part
        pushd clamms.part
        set ee
        make -j
        set +e
        popd
        mv clamms.part clamms
    fi
    echo "export CLAMMS_DIR=$dst_dir/clamms" >> $dst_dir/setenv.sh
fi

# - xhmm
#   Preflight: check for LAPACK/BLAS and warn if missing
if ! ldconfig -p 2>/dev/null | grep -q liblapack; then
    echo "Warning: LAPACK not found (liblapack). XHMM build may fail."
    echo "         On Debian/Ubuntu install: sudo apt install -y liblapack-dev libblas-dev"
fi
xhmm --version >/dev/null 2>&1
if [ "$?" != "0" ]; then
    if [ ! -e xhmm/xhmm ]; then
        git clone --depth 1 https://bitbucket.org/statgen/xhmm.git xhmm.part
        pushd xhmm.part
        set -e
        # make it compile with newer versions of the compiler
        sed -i.bak 's/^CXXFLAGS.*/CXXFLAGS = -std=c++11 -Wall -O3 $(DBGCXXFLAGS)/ ; s/^ALL_CFLAGS.*/ALL_CFLAGS = -std=c99 -O3 -DSQLITE_OMIT_LOAD_EXTENSION $(LIB_INCLUDE_FLAGS)/' ./sources/hmm++/config_defs.Makefile
        make
        set +e
        popd
        mv xhmm.part xhmm
    fi
    echo 'export PATH='$dst_dir'/xhmm:$PATH' >> $dst_dir/setenv.sh
fi

. $dst_dir/setenv.sh

