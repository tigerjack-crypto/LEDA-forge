from cryptographic_estimators.SDEstimator import SDEstimator, BJMM, BJMMpdw, BJMMplus, BJMMdw, BothMay
# assuming ISD(n,r,t)

MEM_CONST = 0
MEM_LOG = 1
MEM_SQRT = 2
MEM_CBRT = 3

def isd_compute(n: int, r: int, t: int, skip_algos, memory_access=MEM_LOG):
    # SDEstimator requires n,k,t as params
    sd = SDEstimator(n,
                     n - r,
                     t,
                     excluded_algorithms=skip_algos,
                     memory_access=memory_access)
    res = sd.estimate()
    min_time = min(res.items(), key=lambda algo: algo['estimate']['time'])

    return min_time["time"]

    # best = { "name": "Prange",
    #          "time" : res["Prange"]["estimate"]["time"],
    #          "memory": res["Prange"]["estimate"]["memory"]}
    # for algo in res:
    #     if best["time"] > res[algo]["estimate"]["time"]:
    #         best["name"] = algo
    #         best["time"] = res[algo]["estimate"]["time"]
    #         best["memory"] = res[algo]["estimate"]["memory"]
    #print(f'Best algorithm {best}')
    # res["best"] = best
    # print(res)
