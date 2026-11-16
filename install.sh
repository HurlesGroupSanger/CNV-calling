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
    exit 1;
fi

# Check prerequisites which are not installed below.
check_commands()
{
    local cmd missing=0
    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            echo "Missing dependency: $cmd" >&2
            missing=1
        fi
    done
    return $missing
}
check_commands git realpath perl java Rscript bedtools python3 patch awk sed sort grep head tail cut gzip gunzip zless less cat cp mv rm mkdir dirname touch || exit 1
Rscript -e 'library(FNN); library(ExomeDepth)' || exit 1
java -version >/dev/null 2>&1 || exit 1
bedtools --version >/dev/null 2>&1 || exit 1

mkdir -p "$1" || exit 1
dst_dir=`realpath "$1"` || exit 1

download_main=0
script=$0
if [ $script != "bash" ]; then
    dir=`dirname $script`
    if [ "$dir" = ""  ]; then dir="."; fi
    dir=`realpath $dir`
    if [ ! -e "$dir/src/run-clamms" ]; then
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
pushd "$dst_dir" || exit 1

# Download the components:
# - this CNV-calling pipeline
set -e
if [ $download_main = "1" ] && [ ! -e "CNV-calling" ]; then
    git clone --depth 1 https://github.com/HurlesGroupSanger/CNV-calling.git
fi
if [ $download_main = "1" ]; then dir="$dst_dir/CNV-calling"; fi
set +e

# - vr-runner pipeline
perl -MRunner -e1 2>/dev/null
if [ "$?" != "0" ]; then
    if [ ! -e vr-runner/modules ]; then
        git clone --depth 1 https://github.com/VertebrateResequencing/vr-runner.git || exit 1
    fi
    echo 'export PATH='$dst_dir'/vr-runner/scripts:$PATH' >> $dst_dir/setenv.sh
    echo 'export PERL5LIB='$dst_dir'/vr-runner/modules:$PERL5LIB' >> $dst_dir/setenv.sh
fi

# - run-convex pipeline
run-convex +sampleconf 2>/dev/null
if [ "$?" != "111" ]; then
    if [ ! -e CoNVex/utils/run-convex ]; then
        git clone --depth 1 https://github.com/HurlesGroupSanger/CoNVex.git || exit 1
    fi
    echo 'export PATH='$dst_dir'/CoNVex/utils:$PATH' >> $dst_dir/setenv.sh
fi

# - samtools, annot-tsv
version=1.22
samtools  --version >/dev/null 2>&1; has_samtools=$(( $? != 0 ))
if [ "$has_samtools" -eq 0 ]; then
    samtools bedcov 2>&1 | grep -q -- '-c ' || has_samtools=1
fi
annot-tsv --version >/dev/null 2>&1; has_annot_tsv=$(( $? != 0 ))
if [ "$has_samtools" -ne 0 ] || [ "$has_annot_tsv" -ne 0 ]; then
    if [ ! -e samtools-$version/samtools ]; then
        check_commands wget tar bzip2 make gcc || exit 1
        set -e
        echo "need samtools"
        wget https://github.com/samtools/samtools/releases/download/$version/samtools-$version.tar.bz2
        tar xjf samtools-$version.tar.bz2
        pushd samtools-$version
        cd htslib-$version
        ./configure
        make -j
        cd ..
        ./configure
        make -j
        set +e
        popd
    fi
    echo 'export PATH='$dst_dir'/samtools-'$version':$PATH' >> $dst_dir/setenv.sh
    echo 'export PATH='$dst_dir'/samtools-'$version'/htslib-'$version':$PATH' >> $dst_dir/setenv.sh
fi

# - clamms
: "${CLAMMS_DIR:=$dst_dir/clamms}"
CLAMMS_DIR=`realpath "$CLAMMS_DIR"` || exit 1
"$CLAMMS_DIR/call_cnv" >/dev/null 2>&1
if [ "$?" != "1" ]; then
    if [ ! -e "$CLAMMS_DIR/call_cnv" ]; then
        check_commands make gcc || exit 1
        set -e
        git clone --depth 1 https://github.com/rgcgithub/clamms.git "$CLAMMS_DIR.part"
        pushd "$CLAMMS_DIR.part"
        make -j
        set +e
        popd
        mv "$CLAMMS_DIR.part" "$CLAMMS_DIR" || exit 1
    fi
fi
for cmd in call_cnv fit_models normalize_coverage annotate_windows.sh calc_window_mappability.py; do
    if [ ! -x "$CLAMMS_DIR/$cmd" ]; then
        echo "Missing CLAMMS executable: $CLAMMS_DIR/$cmd" >&2
        exit 1
    fi
done
# Port the upstream helper; leave an already ported installation intact.
if patch --dry-run --batch --forward -p1 -d "$CLAMMS_DIR" < "$dir/patches/clamms-python3.patch" >/dev/null 2>&1; then
    patch --batch --forward -p1 -d "$CLAMMS_DIR" < "$dir/patches/clamms-python3.patch" || exit 1
fi
python3 -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' "$CLAMMS_DIR/calc_window_mappability.py" || {
    echo "CLAMMS helper is incompatible with python3; check patches/clamms-python3.patch against the installed version." >&2
    exit 1
}
# A separately ported helper may still use the unversioned interpreter name.
if grep -q '^#!/usr/bin/env python$' "$CLAMMS_DIR/calc_window_mappability.py"; then
    sed -i.bak '1s,#!/usr/bin/env python$,#!/usr/bin/env python3,' "$CLAMMS_DIR/calc_window_mappability.py" || exit 1
fi
echo "export CLAMMS_DIR='$CLAMMS_DIR'" >> $dst_dir/setenv.sh

# - xhmm
xhmm --version >/dev/null 2>&1
if [ "$?" != "0" ]; then
    if [ ! -e xhmm/xhmm ]; then
        check_commands make gcc g++ || exit 1
        set -e
        git clone --depth 1 https://bitbucket.org/statgen/xhmm.git xhmm.part
        pushd xhmm.part
        # make it compile with newer versions of the compiler
        sed -i.bak 's/^CXXFLAGS.*/CXXFLAGS = -std=c++11 -Wall -O3 $(DBGCXXFLAGS)/ ; s/^ALL_CFLAGS.*/ALL_CFLAGS = -std=c99 -O3 -DSQLITE_OMIT_LOAD_EXTENSION $(LIB_INCLUDE_FLAGS)/' ./sources/hmm++/config_defs.Makefile
        make
        set +e
        popd
        mv xhmm.part xhmm || exit 1
    fi
    echo 'export PATH='$dst_dir'/xhmm:$PATH' >> $dst_dir/setenv.sh
fi

. $dst_dir/setenv.sh || exit 1
perl -MRunner -e1 || exit 1
samtools bedcov 2>&1 | grep -q -- '-c ' || exit 1
annot-tsv --version >/dev/null 2>&1 || exit 1
xhmm --version >/dev/null 2>&1 || exit 1
echo "Configure Picard/GATK commands, XHMM params.txt and reference files before running."
echo "Runner defaults to LSF; use +local for serial execution or +js slurm for SLURM."

