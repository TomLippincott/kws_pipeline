import sys
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
    ("BABEL_RESOURCES", "", None),
    ("F4DE", "", None),
    ("INDUS_DB", "", None),
    ("JAVA_NORM", "", "${BABEL_REPO}/KWS/examples/babel-dryrun/javabin"),
    ("OVERLAY", "", None),
    ("LIBRARY_OVERLAY", "", "${OVERLAY}/lib:${OVERLAY}/lib64"),
    ("EXPERIMENTS", "", {}),
    ("LOG_LEVEL", "", logging.INFO),
    ("LOG_DESTINATION", "", sys.stdout),
    )

#
# create the actual build environment we'll be using: basically, just import the builders from site_scons/kws_tools.py
#
env = Environment(variables=vars, ENV={}, TARFLAGS="-c -z", TARSUFFIX=".tgz",
                  tools=["default", "textfile"] + [x.TOOLS_ADD for x in [kws_tools]],
                  BUILDERS={"CopyFile" : Builder(action="cp ${SOURCE} ${TARGET}")}
                  )

#
# initialize the Python logging system (though we don't really use it in this build, could be useful later)
#
if isinstance(env["LOG_DESTINATION"], basestring):
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"], filename=env["LOG_DESTINATION"])
else:
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=env["LOG_LEVEL"])

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
    iv_dict = experiment["IV_DICTIONARY"]
    oov_dict = experiment["OOV_DICTIONARY"]
    dbfile = experiment["DATABASE"]
    kw_file = experiment["KW_FILE"]

    iv_query_terms, oov_query_terms, term_map, word_to_word_fst, kw_file = env.QueryFiles([os.path.join(base_path, x) for x in ["iv_queries.txt", 
                                                                                                                                "oov_queries.txt",
                                                                                                                                "term_map.txt",
                                                                                                                                "word_to_word.fst",
                                                                                                                                "kwfile.xml"]], [kw_file, iv_dict])

    #iv_query_terms, oov_query_terms, term_map, kw_file, word_to_word_fst = env.AlterIVOOV([os.path.join(base_path, x) for x in 
    #                                                                                       ["iv_terms.txt", "oov_terms.txt", "term_map.txt", "kw_file.xml", "word_to_word.fst"]], 
    #                                                                                      [iv_query_terms, oov_query_terms, iv_dict, term_map, kw_file, word_to_word_fst])
    #word_to_word_fst = env.WordToWordFST(os.path.join(base_path, "word_to_word.fst"), [])
    #dbfile = env.DatabaseFile(os.path.join(base_path, "dbfile.txt"), env.Value(experiment["LATTICE_DIRECTORY"]))
    
    full_lattice_list = env.LatticeList(os.path.join(base_path, "lattice_list.txt"),
                                        [dbfile, env.Value(experiment["LATTICE_DIRECTORY"])])



    lattice_lists = env.SplitList([os.path.join(base_path, "lattice_list_%d.txt" % (n + 1)) for n in range(experiment["JOBS"])], full_lattice_list)

    wordpron = env.WordPronounceSymTable(os.path.join(base_path, "in_vocabulary_symbol_table.txt"),
                                         iv_dict)

    isym = env.CleanPronounceSymTable(os.path.join(base_path, "cleaned_in_vocabulary_symbol_table.txt"),
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

    ecf_file = env.ECFFile(os.path.join(base_path, "ecf.xml"), mdb)

    data_lists = env.SplitList([os.path.join(base_path, "data_list_%d.txt" % (n + 1)) for n in range(experiment["JOBS"])], full_data_list)
    
    p2p_fst = env.FSTCompile(os.path.join(base_path, "p2p_fst.txt"),
                             [isym, word_to_word_fst])

    wtp_lattices = []


    for i, (data_list, lattice_list) in enumerate(zip(data_lists, lattice_lists)):
        wp = env.WordToPhoneLattice(os.path.join(base_path, "lattices", "lattice_generation-%d.stamp" % (i + 1)), 
                                    [data_list, lattice_list, wordpron, iv_dict, env.Value({"PRUNE_THRESHOLD" : -1,
                                                                                            "EPSILON_SYMBOLS" : "'<s>,</s>,~SIL,<HES>'",
                                                                                            })])

        fl = env.GetFileList(os.path.join(base_path, "file_list-%d.txt" % (i + 1)), 
                             [data_list, wp])
        idx = env.BuildIndex(os.path.join(base_path, "index-%d.fst" % (i + 1)),
                             fl)

        wtp_lattices.append((wp, data_list, lattice_list, fl, idx))

    merged = {}
    for query_type, query_file in zip(["in_vocabulary", "out_of_vocabulary"], [iv_query_terms, oov_query_terms]):
        queries = env.QueryToPhoneFST(os.path.join(base_path, query_type, "query.fst"), 
                                      [p2p_fst, isym, iv_dict, query_file, env.Value({"n" : 1, "I" : 1, "OUTDIR" : os.path.join(base_path, query_type, "queries")})])
        searches = []
        for i, (wtp_lattice, data_list, lattice_list, fl, idx) in enumerate(wtp_lattices):
            searches.append(env.StandardSearch(os.path.join(base_path, query_type, "search_output-%d.txt" % (i + 1)),
                                               [data_list, isym, idx, padfst, queries, env.Value({"PRECISION" : "'%.4d'", "TITLE" : "std.xml"})]))



        qtl, res_list, res, ures = env.Merge([os.path.join(base_path, query_type, x) for x in ["ids_to_query_terms.txt", "result_file_list.txt", "search_results.xml", "unique_search_results.xml"]], 
                                             [query_file] + searches + [env.Value({"MODE" : "merge-default",
                                                                                   "PADLENGTH" : 4,                                    
                                                                                   "PREFIX" : ""})])

        merged[query_type] = ures
        om = env.MergeScores(os.path.join(base_path, query_type, "results.xml"), 
                             res)

    iv_oov = env.MergeIVOOV(os.path.join(base_path, "iv_oov_results.xml"), 
                            [merged["in_vocabulary"], merged["out_of_vocabulary"], term_map])

    norm = env.Normalize(os.path.join(base_path, "norm.kwslist.xml"), 
                         [iv_oov, kw_file])

    normSTO = env.NormalizeSTO(os.path.join(base_path, "normSTO.kwslist.xml"), 
                               norm)

    score = env.Score([os.path.join(base_path, x) for x in ["score.sum.txt", "score.bsum.txt"]], 
                      [norm, kw_file, env.Value({"RTTM_FILE" : experiment["RTTM_FILE"], "ECF_FILE" : ecf_file[0].rstr()})]) #experiment)])

    scoreSTO = env.Score([os.path.join(base_path, "%s.STO.txt" % x) for x in ["score.sum", "score.bsum"]], 
                         [normSTO, kw_file, env.Value({"RTTM_FILE" : experiment["RTTM_FILE"], "ECF_FILE" : ecf_file[0].rstr()})]) #experiment)])
