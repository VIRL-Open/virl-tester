#!/bin/bash

CYCLES=100
BREAK=0
LOG="main.log"

stopit () { BREAK=1; }


awk_cmd='
function ptime(t) {
  s = sprintf("%dm%02ds", int(t/60), t%60)
  return s
}

BEGIN {
  hi = 0;
  lo = 32768;
  sum = 0;
  cycles = 0;
  failed = 0;
  tests = 0
  sims = 0
}

/[[:digit:]]+ out of [[:digit:]]+/ {
  tmp = match($0, /([[:digit:]]+) out of ([[:digit:]]+)/, a)
  if(tmp) {
    _all = int(a[2])
    _fail = _all-int(a[1])
    failed += _fail
    tests += _all
  }
  cycles += 1;
}

/new thread.*\.virl/ {
  sims += 1
}

/^real/ {
  split($2, a, "m");
  time = int(a[1]) * 60 + a[2];
  sum += time;
  if (time > hi) hi = time;
  if (time < lo) lo = time;
}

END {
  if (cycles > 0) {
    avg = sum / cycles;
    printf("Cycles: %d Sims: %d Tests: %d Failed: %d Last: %s Low: %s High: %s Average: %s",
      cycles, sims, tests, failed, ptime(time), ptime(lo), ptime(hi), ptime(avg));
  }
}
'


status () {
    cat $LOG | awk "$awk_cmd" 
}

trap stopit SIGINT

CMD=$*
[ -z "$CMD" ] && CMD="allnodes.yml"

echo "Doing $CYCLES runs of $CMD..."

for i in $(seq $CYCLES); do 
    { time virltester $CMD ;} >>$LOG 2>&1
    test $BREAK -eq 1 && break
    status
done
echo -e "\nDone!"
