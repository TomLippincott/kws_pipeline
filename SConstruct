import os.path
import logging
import kws_tools

#
# load variable definitions from custom.py, and define them for SCons (seems like it should logically
# happen in the reverse order, but anyways...)
#
vars = Variables("custom.py")
vars.AddVariables(
    ("OUTPUT_WIDTH", "", 130),
    ("BABEL_REPO", "", None),
    ("F4DE", "", None),
    ("INDUS_DB", "", None),
    ("JAVA_NORM", "", "${BABEL_REPO}/KWS/examples/babel-dryrun/javabin"),
    ("OVERLAY", "", None),
    ("LIBRARY_OVERLAY", "", "${OVERLAY}/lib:${OVERLAY}/lib64"),
    ("EXPERIMENTS", "", {}),
    )


#
# initialize the Python logging system (though we don't really use it in this build, could be useful later)
#
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

#
# create the actual build environment we'll be using: basically, just import the builders from site_scons/kws_tools.py
#
env = Environment(variables=vars, ENV={}, TARFLAGS="-c -z", TARSUFFIX=".tgz",
                  tools=["default", "textfile"] + [x.TOOLS_ADD for x in [kws_tools]],
                  BUILDERS={"CopyFile" : Builder(action="cp ${SOURCE} ${TARGET}")}
                  )

#
# each Builder emits a string describing what it's doing (target, source, etc), but with thousands of
# input files, this can be huge.  If the string is larger than OUTPUT_WIDTH, replace some of its
# characters with an ellipsis.  You can get less-truncated output by running e.g. "scons -Q OUTPUT_WIDTH=300"
#
def print_cmd_line(s, target, source, env):
    if len(s) > int(env["OUTPUT_WIDTH"]):
        print s[:int(env["OUTPUT_WIDTH"]) - 10] + "..." + s[-7:]
    else:
        print s
env['PRINT_CMD_LINE_FUNC'] = print_cmd_line

#
# check whether custom.py has defined all the variables we need
#
undefined = [x for x in vars.keys() if x not in env]
if len(undefined) != 0:
    print """
One or more parameters (%s) are undefined.  Please edit custom.py appropriately.
To get started, 'cp custom.py.example custom.py'
""" % (",".join(undefined))
    env.Exit()

#
# run all the experiments in EXPERIMENTS (defined in custom.py)
#
for name, experiment in env["EXPERIMENTS"].iteritems():
    
    # all output goes under "work/EXPERIMENT_NAME"
    base_path = os.path.join("work", name)

    # just make some local variables from the experiment definition (for convenience)
    word_to_word_fst = experiment["WORD_TO_WORD_FST"]
    iv_dict = experiment["IV_DICTIONARY"]
    oov_dict = experiment["OOV_DICTIONARY"]
    dbfile = experiment["DATABASE"]
    iv_query_terms = experiment["IV_QUERY_TERMS"]
    oov_query_terms = experiment["OOV_QUERY_TERMS"]
    term_map = experiment["TERM_MAP"]

    full_lattice_list = env.LatticeList(os.path.join(base_path, "lattice_list.txt"),
                                        [dbfile, env.Value(experiment["LATTICE_DIRECTORY"])])

    wordpron = env.WordPronounceSymTable(os.path.join(base_path, "in_vocabulary_sym_table.txt"),
                                         iv_dict)

    isym = env.CleanPronounceSymTable(os.path.join(base_path, "cleaned_in_vocabulary_sym_table.txt"),
                                      wordpron)

    mdb = env.MungeDatabase(os.path.join(base_path, "munged_database.txt"),
                            [dbfile, full_lattice_list])

    padfst = env.BuildPadFST(os.path.join(base_path, "pad_fst.txt"),
                             wordpron)

    full_data_list = env.CreateDataList(os.path.join(base_path, "full_data_list.txt"),
                                        [mdb] + [env.Value({"oldext" : "fsm.gz", 
                                                            "ext" : "fst",
                                                            "subdir_style" : "hub4",
                                                            "LATTICE_DIR" : experiment["LATTICE_DIRECTORY"],
                                                            })], BASE_PATH=base_path)
    
    p2p_fst = env.FSTCompile(os.path.join(base_path, "p2p_fst.txt"),
                             [isym, word_to_word_fst])

    data_lists = env.SplitList([os.path.join(base_path, "data_list_%d.txt" % (n + 1)) for n in range(experiment["JOBS"])],
                               [full_data_list, env.Value({"n" : experiment["JOBS"]})], BASE_PATH=os.path.join(base_path, "data_lists"))

    lattice_lists = env.SplitList([os.path.join(base_path, "lattice_list_%d.txt" % (n + 1)) for n in range(experiment["JOBS"])],
                                  [full_lattice_list, env.Value({"n" : experiment["JOBS"]})], BASE_PATH=os.path.join(base_path, "lattice_lists"))


    wtp_lattices = []


    for i, (data_list, lattice_list) in enumerate(zip(data_lists, lattice_lists)):
        wp = env.WordToPhoneLattice(os.path.join(base_path, "lattices", "lattice_generation-%d.stamp" % (i + 1)), 
                                    [data_list, lattice_list, wordpron, iv_dict, env.Value({"PRUNE_THRESHOLD" : 6,
                                                                                            "EPSILON_SYMBOLS" : "'<s>,</s>,~SIL,<HES>'",
                                                                                            })])

        fl = env.GetFileList(os.path.join(base_path, "file_list-%d.txt" % (i + 1)), 
                             [data_list, wp])
        idx = env.BuildIndex(os.path.join(base_path, "index-%d.txt" % (i + 1)),
                             fl)

        wtp_lattices.append((wp[0], data_list, lattice_list, fl, idx))

    merged = {}
    for query_type, query_file in zip(["in_vocabulary", "out_of_vocabulary"], [iv_query_terms, oov_query_terms]):
        queries = env.QueryToPhoneFST(os.path.join(base_path, query_type, "query.fst"), 
                                      [p2p_fst, isym, iv_dict, query_file, env.Value({"n" : 1, "I" : 1, "OUTDIR" : os.path.join(base_path, query_type, "queries")})])
        searches = []
        for i, (wtp_lattice, data_list, lattice_list, fl, idx) in enumerate(wtp_lattices):
            searches.append(env.StandardSearch(os.path.join(base_path, query_type, "search_output-%d.txt" % (i + 1)),
                                               [data_list, isym, idx, padfst, queries, env.Value({"PRECISION" : "'%.4d'", "PREFIX" : "KW106-", "TITLE" : "std.xml"})]))



        qtl, res_list, res, ures = env.Merge([os.path.join(base_path, query_type, x) for x in ["ids_to_query_terms.txt", "result_file_list.txt", "search_results.xml", "unique_search_results.xml"]], 
                                             [query_file] + searches + [env.Value({"MODE" : "merge-default",
                                                                                   "PADLENGTH" : 4,                                    
                                                                                   "PREFIX" : "KW106-"})])
        merged[query_type] = ures
        om = env.MergeScores(os.path.join(base_path, query_type, "res"), 
                             res)

    iv_oov = env.MergeIVOOV(os.path.join(base_path, "iv_oov_results.txt"), 
                            [merged["in_vocabulary"], merged["out_of_vocabulary"], term_map])

    norm = env.Normalize(os.path.join(base_path, "norm.txt"), 
                         iv_oov)

    normSTO = env.NormalizeSTO(os.path.join(base_path, "normSTO.txt"), 
                               norm)

    # score = env.Score(os.path.join(base_path, "score.txt"), 
    #                   [norm, env.Value(experiment)])

    # scoreSTO = env.Score(os.path.join(base_path, "scoreSTO.txt"), 
    #                      [normSTO, env.Value(experiment)])
