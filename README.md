kws_pipeline
============

Keyword Search Pipeline

Quick Start

This SCons build is designed to run keyword search (KWS) on the output from the IBM Atilla 
automatic speech recognition (ASR) system.  SCons itself, and other libraries needed for 
the build, are installed under /export/projects/nlp/tools/overlay_fc11.  To configure your 
environment, simply run:

  source /export/projects/nlp/tools/overlay_fc11/bashrc.txt

To run the example experiment, copy the basic configuration:

  cp custom.py.example custom.py

and edit "custom.py", removing any initial *single* hashmarks (double hashmarks are actual
comments).  Then, you can see what SCons will do by running:

  scons -Qn

Finally, you can run the build, specifying the number of processes with the "-j" switch:

  scons -Q -j 5

On panini.ldeo.columbia.edu, if there are five unused cores available, this will take about
20 minutes to complete.

How it works (in three files)

The SConstruct file is like a Makefile, with the advantage that it's basically a Python
script.  There are comments in it explaining what each stage does.  For the purposes of
running experiments, we don't want to have to change it very often.  It defines the
dependencies between the stages of the KWS pipeline, which are already known.

The custom.py file, on the other hand, is where we define experiments (and environment
variables, but these should be fairly static since we're only running it here at CCLS).
Each item in the EXPERIMENTS list variable is a map of names to values, defining an
experiment.  The SConstruct file imports all the variables in custom.py, and runs each
experiment in the EXPERIMENTS variable.

Finally, the real heart is in site_scons/kws_tools.py.  This file defines "builders", which
are Python functions of signature (target, source, env) and perform the work to create
"target" from "source", possibly via information contained in "env".  The current builders
are based on IBM's script-based system, specifically the example living in:

  /export/projects/nlp/BABEL/lorelei_svn/KWS/examples/babel-tagalog-fulllp/

Unfortunately, the entire process, both configurations and executables, is spread out in
both child and parent (!) directories, a real rats' nest.  Also, they are continuously
releasing new versions, such as those under:

  /export/projects/nlp/BABEL/lorelei_svn/KWS/resources-bpEval

Current State

Right now, I believe everything is working up until the very final "scoring" action, which
is BABEL12_Scorer/BABEL13_Scorer/KWSEval.py or something similar, depending on which
version you look at.  

There is a first attempt at scoring, which you can see as the commented code at the end of
site_scons/kws_tools.py and the final two comments at the end of SConstruct.  It doesn't
work, but a fair number of the ugly boilerplate that will be necessary, such as a bunch
of Perl libraries, have been installed under /export/projects/nlp/tools/overlay_fc11.

Text::CSV
Statistics::Descriptive
Math::Random::OO
xmllint