import resource, runpy, sys, time
t = time.time()
sys.argv = sys.argv[1:]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    print(f"MEMRUN peak RSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**30:.2f} GiB, wall {time.time()-t:.0f} s", file=sys.stderr)
