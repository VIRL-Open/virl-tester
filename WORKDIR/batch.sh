#!/bin/bash

CYCLES=100
BREAK=0
LOG="main.log"

stopit () { BREAK=1; }

awk_cmd='
function ptime(t) {
  s=sprintf("%dm%ds", int(t/60), t%60)
  return s
}

BEGIN {
  hi=0;
  lo=32768;
  sum=0;
  count=0;
  failed=0;
}

/fail/ {
  failed+=1;
}

/real/ {
  split($2,a,"m");
  time=int(a[1])*60+a[2];
  sum+=time;
  if (time>hi) hi=time;
  if (time<lo) lo=time;
  count+=1;
}

END {
  if (count > 0) {
    avg=sum/count;
    printf("\rCycles: %d Failed: %d Low: %s High: %s Average: %s",
      count, failed, ptime(lo), ptime(hi), ptime(avg));
  }
}
'


status () {
    cat $LOG | awk "$awk_cmd" 
}

trap stopit SIGINT

CMD=$*
[ -z "$CMD" ] && CMD="allnodes.yml"

echo $CMD

for i in $(seq $CYCLES); do 
    { time virltester $CMD ;} >>$LOG 2>&1
    test $BREAK -eq 1 && break
    status
done
echo -e "\nDone!"

