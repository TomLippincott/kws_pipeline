from SCons.Builder import Builder
from SCons.Action import Action
import re
from glob import glob
from functools import partial
import logging
import os.path
import os
import cPickle as pickle
import math
import xml.etree.ElementTree as et
import gzip
import subprocess
import shlex
import time

#def run_command(cmd, overlay="", f4de_base=""):
def run_command(cmd, env={}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    simple convenience wrapper for running commands (not an actual Builder)
    """
    #process = subprocess.Popen(shlex.split(cmd), env={"LD_LIBRARY_PATH" : overlay, "F4DE_BASE" : "%s" % f4de_base, "PERL5LIB" : "%s/lib/perl5/site_perl/:%s/common/lib:%s/KWSEval/lib" % (overlay, f4de_base, f4de_base), "F4DE_XMLLINT" : "/usr/bin/xmllint"}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #stdout, stderr = process.communicate()
    #return stdout, stderr, process.returncode
    process = subprocess.Popen(shlex.split(cmd), env=env, stdin=stdin, stdout=stdout, stderr=stderr)
    out, err = process.communicate()
    return out, err, process.returncode == 0

def lattice_list(target, source, env):
    """
    creates a file that's simply a list of the input files (absolute paths, one per line)
    """
    with open(source[0].rstr()) as fd:
        db_files = set(["%s.fsm.gz" % ("#".join(x.split()[0:2])) for x in fd])
    lattice_dir = source[1].read()
    if not os.path.exists(lattice_dir):
        return "No such directory: %s" % lattice_dir
    open(target[0].rstr(), "w").write("\n".join([os.path.abspath(x) for x in glob(os.path.join(lattice_dir, "*")) if os.path.basename(x) in db_files]) + "\n")
    return None

def word_pronounce_sym_table(target, source, env):
    """
    convert dictionary format
    """
    ofd = open(target[0].rstr(), "w")
    ofd.write("<EPSILON>\t0\n")
    for i, line in enumerate(gzip.open(source[0].rstr())):
        ofd.write("%s\t%d\n" % (line.split()[0], i + 1))
    ofd.close()
    return None

def clean_pronounce_sym_table(target, source, env):
    ofd = open(target[0].rstr(), "w")
    seen = set()
    for line in open(source[0].rstr()):
        if line.startswith("<EPSILON>"):
            word = "<EPSILON>"
        else:
            word = re.match(r"^(.*)\(\d+\)\s+.*$", line).groups()[0]
        if word not in seen:
            ofd.write("%s\t%d\n" % (word, len(seen)))
            seen.add(word)
    ofd.write("<query>\t%d\n" % (len(seen)))
    return None

def munge_dbfile(target, source, env):
    """
    convert db format
    """
    with open(source[1].rstr()) as fd:
        lattice_files = set([os.path.basename(x.strip()) for x in fd])

    ofd = open(target[0].rstr(), "w")
    for line in open(source[0].rstr()):
        toks = line.split()
        fname = "%s.fsm.gz" % ("#".join(toks[0:2]))
        if fname in lattice_files:
            ofd.write(" ".join(toks[0:4] + ["0.0", toks[5]]) + "\n")
    ofd.close()
    return None

def create_data_list(target, source, env):
    args = source[-1].read()
    data = {}
    for line in open(source[0].rstr()):
        toks = line.split()
        bn = os.path.basename(toks[2])
        data[toks[0]] = data.get(toks[0], {})
        data[toks[0]][toks[1]] = (bn, toks[4], toks[5])
    ofd = open(target[0].rstr(), "w")
    for lattice_file in glob(os.path.join(args["LATTICE_DIR"], "*")):
        bn = os.path.basename(lattice_file)
        path = os.path.join(env["BASE_PATH"], "lattices")
        uttname, delim, uttnum = re.match(r"(.*)([^\w])(\d+)\.%s$" % (args["oldext"]), bn).groups()
        try:
            name, time, timeend = data[uttname][uttnum]
            newname = os.path.abspath(os.path.join(path, "%s%s%s.%s" % (uttname, delim, uttnum, args["ext"])))
            ofd.write("%s %s %s %s %s.osym %s\n" % (os.path.splitext(name)[0], time, timeend, newname, newname, os.path.abspath(lattice_file)))
        except:
            return "lattice file not found in database: %s (are you sure your database file matches your lattice directory?)" % bn
    ofd.close()
    return None

def split_list(target, source, env):
    lines = [x for x in open(source[0].rstr())]
    per_file = len(lines) / len(target)
    for i, fname in enumerate(target):
        start = int((i * float(len(lines))) / len(target))
        end = int(((i + 1) * float(len(lines))) / len(target))
        if i == len(target) - 1:
            open(fname.rstr(), "w").write("".join(lines[start : ]))
        else:
            open(fname.rstr(), "w").write("".join(lines[start : end]))
    return None

def word_to_phone_lattice(target, source, env):
    args = source[-1].read()
    data_list, lattice_list, wordpron, dic = source[0:4]
    args["DICTIONARY"] = dic.rstr()
    args["DATA_FILE"] = data_list.rstr()
    args["FSMGZ_FORMAT"] = "true"
    args["CONFUSION_NETWORK"] = ""
    args["FSM_DIR"] = "temp"
    args["WORDPRONSYMTABLE"] = wordpron.rstr()
    cmd = env.subst("${BABEL_REPO}/KWS/bin64/wrd2phlattice")
    argstr = "-d %(DICTIONARY)s -D %(DATA_FILE)s -t %(FSMGZ_FORMAT)s -s %(WORDPRONSYMTABLE)s -S %(EPSILON_SYMBOLS)s %(CONFUSION_NETWORK)s -P %(PRUNE_THRESHOLD)d %(FSM_DIR)s" % args
    if not os.path.exists(os.path.dirname(target[0].rstr())):
        os.makedirs(os.path.dirname(target[0].rstr()))
    stdout, stderr, success = run_command("%s %s" % (cmd, argstr), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=open(lattice_list.rstr()), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not success:
        return stderr
    else:
        open(target[0].rstr(), "w").write("%s" % (time.time()))
    return None

def get_file_list(target, source, env):
    open(target[0].rstr(), "w").write("\n".join([x.split()[3] for x in open(source[0].rstr())]))
    return None

def build_index(target, source, env):
    command = env.subst("${BABEL_REPO}/KWS/bin64/buildindex -p ${SOURCE} ${TARGET}", target=target, source=source)
    #process = subprocess.Popen(shlex.split(command), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, success = run_command(command, env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #= process.communicate()

    if not success:
        return stderr
    return None

def build_pad_fst(target, source, env):
    command = env.subst("${BABEL_REPO}/KWS/bin64/buildpadfst ${SOURCE} ${TARGET}", target=target, source=source)
    #process = subprocess.Popen(shlex.split(command), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, success = run_command(command, env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #= process.communicate()
    if not success:
        return stderr
    return None

def fst_compile(target, source, env):
    command = env.subst("${OVERLAY}/bin/fstcompile --isymbols=${SOURCES[0]} --osymbols=${SOURCES[0]} ${SOURCES[1]}", target=target, source=source)
    #process = subprocess.Popen(shlex.split(command), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, success = run_command(command, env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #= process.communicate()
    if not success: #process.returncode != 0:
        return stderr
    open(target[0].rstr(), "w").write(stdout)
    return None

def query_to_phone_fst(target, source, env):
    args = source[-1].read()
    try:
        os.makedirs(args["OUTDIR"])
    except:
        pass
    command = env.subst("${BABEL_REPO}/KWS/bin64/query2phonefst -p ${SOURCES[0]} -s ${SOURCES[1]} -d ${SOURCES[2]} -l ${TARGETS[0]} -n %(n)d -I %(I)d %(OUTDIR)s ${SOURCES[3]}" % args, target=target, source=source)
    #process = subprocess.Popen(shlex.split(command), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, success = run_command(command, env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #= process.communicate()
    if not success: #process.returncode != 0:
        return stderr
    return None

def standard_search(target, source, env):
    data_list, isym, idx, pad, queryph = source[0:5]
    args = source[-1].read()
    command = env.subst("${BABEL_REPO}/KWS/bin64/stdsearch -F ${TARGET} -i ${SOURCES[2]} -b %(PREFIX)s -s ${SOURCES[1]} -p ${SOURCES[3]} -d ${SOURCES[0]} -a %(TITLE)s -m %(PRECISION)s ${SOURCES[4]}" % args, target=target, source=source)
    #process = subprocess.Popen(shlex.split(command), env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, success = run_command(command, env={"LD_LIBRARY_PATH" : env.subst(env["LIBRARY_OVERLAY"])}, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #= process.communicate()
    if not success: #process.returncode != 0:
        return stderr
    return None

def merge(target, source, env):
    """
    Combines the output of several searches
    input: XML files (<term>)
    output: 
    """
    args = source[-1].read()
    stdout, stderr, success = run_command(env.subst("${BABEL_REPO}/KWS/scripts/printQueryTermList.prl -prefix=%(PREFIX)s -padlength=%(PADLENGTH)d ${SOURCES[0]}" % args, 
                                                    target=target, source=source), env={"LD_LIBRARY_PATH" : env.subst("${LIBRARY_OVERLAY}")})
    open(target[0].rstr(), "w").write(stdout)
    open(target[1].rstr(), "w").write("\n".join([x.rstr() for x in source[1:-1]]))
    if args["MODE"] == "merge-atwv":
        pass
        #print_query_term_map_list = "${BABEL_REPO}/KWS/scripts/printQueryTermList.prl -prefix=${PREFIX} -padlength=${PADLENGTH} ${QUERY_FILE} > ${QUERY_TERM}"
        #merge_search_from_par_index = "${BABEL_REPO}/KWS/scripts/mergeSearchFromParIndex.prl -hrsaudio=${HOURS} -beta=${BETA} ${QUERY_TERM} ${RESULT_LIST} > ${RESULT}"
    else:        
        merge_search_from_par_index = "${BABEL_REPO}/KWS/scripts/mergeSearchFromParIndex.prl -force-decision=\"YES\" ${TARGETS[0]} ${TARGETS[1]}"
        stdout, stderr, success = run_command(env.subst(merge_search_from_par_index, target=target, source=source), env={"LD_LIBRARY_PATH" : env.subst("${LIBRARY_OVERLAY}")})
        open(target[2].rstr(), "w").write(stdout)
        open(target[3].rstr(), "w").write("\n".join(stdout.split("\n")))
    return None

def merge_scores(target, source, env):
    stdout, stderr, success = run_command(env.subst("${BABEL_REPO}/KWS/scripts/merge.scores.sumpost.norm.pl 1 ${SOURCES[0]}", target=target, source=source), env={"LD_LIBRARY_PATH" : env.subst("${LIBRARY_OVERLAY}")})
    open(target[0].rstr(), "w").write(stdout)
    return None

def merge_iv_oov(target, source, env):
    stdout, stderr, success = run_command(env.subst("perl ${BABEL_REPO}/KWS/scripts/merge_iv_oov.pl ${SOURCES[0]} ${SOURCES[1]} ${SOURCES[2]} ${TARGET}", target=target, source=source), env={"LD_LIBRARY_PATH" : env.subst("${LIBRARY_OVERLAY}")})
    if not success:
        return stderr
    return None

def normalize(target, source, env):
    stdout, stderr, success = run_command(env.subst("python ${BABEL_REPO}/KWS/scripts/F4DENormalization.py ${SOURCE} ${TARGET}", target=target, source=source))
    if not success:
        print stderr
    return None

def normalize_sum_to_one(target, source, env):
    stdout, stderr, success = run_command(env.subst("java -cp ${JAVA_NORM} normalization.ApplySumToOneNormalization ${SOURCE} ${TARGET}", target=target, source=source))
    if not success:
        return stderr
    return None

# def score(target, source, env):
#     args = source[-1].read()
#     if not os.path.exists("work/tempA"):
#         os.mkdir("work/tempA")
#     if not os.path.exists("work/tempB"):
#         os.mkdir("work/tempB")
#     theargs = {}
#     theargs.update(args)
#     theargs.update({"TEMP_DIR" : "work/tempA", "RES_DIR" : "work/tempB", "SYS_FILE" : source[0].rstr()})
#     cmd = env.subst("${F4DE}/KWSEval/tools/KWSEval/KWSEval.pl -sys ${SOURCES[0]} -e %(ECF_FILE)s -r %(RTTM_FILE)s -s %(SYS_FILE)s -t %(KW_FILE)s -f temp -X" % theargs,
#                     source=source, target=target)                    
#     stdout, stderr, success = run_command(cmd, overlay=env["OVERLAY"], f4de_base=env["F4DE"])
#     if not success:
#         print stdout, stderr
#     return None

def TOOLS_ADD(env):
    env.Append(BUILDERS = {'LatticeList' : Builder(action=lattice_list), 
                           'WordPronounceSymTable' : Builder(action=word_pronounce_sym_table), 
                           'CleanPronounceSymTable' : Builder(action=clean_pronounce_sym_table), 
                           'MungeDatabase' : Builder(action=munge_dbfile), 
                           'CreateDataList' : Builder(action=create_data_list), 
                           'SplitList' : Builder(action=split_list), 
                           'WordToPhoneLattice' : Builder(action=word_to_phone_lattice), 
                           'GetFileList' : Builder(action=get_file_list), 
                           'BuildIndex' : Builder(action=build_index), 
                           'BuildPadFST' : Builder(action=build_pad_fst), 
                           'FSTCompile' : Builder(action=fst_compile), 
                           'QueryToPhoneFST' : Builder(action=query_to_phone_fst),
                           'StandardSearch' : Builder(action=standard_search), 
                           'Merge' : Builder(action=merge),
                           'MergeScores' : Builder(action=merge_scores),
                           'MergeIVOOV' : Builder(action=merge_iv_oov),
                           'Normalize' : Builder(action=normalize),
                           'NormalizeSTO' : Builder(action=normalize_sum_to_one),
                           #'Score' : Builder(action=score),
                           })
               
