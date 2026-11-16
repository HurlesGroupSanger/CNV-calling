package CNVRunner;
use base qw(Runner);
use strict;
use warnings;

sub stage_alignment
{
    my ($self,$outfile,$aln) = @_;
    if ( -e $aln or !defined($$self{iget}) ) { return $aln; }
    if ( !($aln =~ /\.(bam|cram)$/i) ) { $self->throw("Expected a BAM or CRAM file: $aln"); }
    my $suffix = lc($1);
    my $bam = "$outfile.$suffix";
    my $index = $suffix eq 'cram' ? 'crai' : 'bai';
    $self->cmd(qq[command -v $$self{iget} >/dev/null]);
    $self->cmd(qq[$$self{iget} -f $aln $bam.part && mv $bam.part $bam]);
    # An index may not be stored in iRODS; build one if retrieval fails.
    unlink("$bam.$index");
    $self->cmd(qq[$$self{iget} -f $aln.$index $bam.$index.part && mv $bam.$index.part $bam.$index],exit_on_error=>0);
    if ( !-e "$bam.$index" )
    {
        unlink("$bam.$index.part");
        $self->cmd(qq[$$self{samtools} index $bam]);
    }
    return $bam;
}

sub clean_alignment
{
    my ($self,$bam,$aln) = @_;
    if ( $bam eq $aln ) { return; }
    unlink($bam);
    unlink("$bam.crai");
    unlink("$bam.bai");
}

1;
