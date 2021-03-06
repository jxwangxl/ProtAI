#!/usr/bin/python

import os
import re
import bs4
import sys
import time
import keras
import Bio.PDB
import datetime
import requests
import argparse
import numpy as np
import pandas as pd
import urllib.request
from Bio import pairwise2
from pyrosetta import *
from pyrosetta.toolbox import *
init()

parser = argparse.ArgumentParser(description='De Novo Protein Design Neural Network')
parser.add_argument('-t', '--train', action='store_true', help='Train the neural network')
args = parser.parse_args()

class RosettaDesign():
	'''
	This class preforms RosettaDesign either fixed backbone
	design (fixbb) or flexible backbone design (flxbb).
	It is preferred to perform the design many times and 
	select the best (lowest) scoring structure.
	'''
	def __init__(self):
		pass

	def BLAST(self, filename1, filename2):
		'''
		Performs a BLAST alignment between two sequences and prints
		the sequences as well as the percentage of sequence
		similarity
		'''
		seq1 = Bio.PDB.Polypeptide.PPBuilder().build_peptides(Bio.PDB.PDBParser(QUIET=True).get_structure('filename1', filename1), aa_only=True)[0].get_sequence()
		seq2 = Bio.PDB.Polypeptide.PPBuilder().build_peptides(Bio.PDB.PDBParser(QUIET=True).get_structure('filename2', filename2), aa_only=True)[0].get_sequence()
		alignment = pairwise2.align.globalxx(seq1, seq2)
		total = alignment[0][4]
		similarity = alignment[0][2]
		percentage = (similarity*100)/total
		print(seq1)
		print(seq2)
		print('Sequence Similarity: {}%'.format(round(percentage, 3)))

	def fixbb(self, filename, relax_iters, design_iters):
		'''
		Performs the RosettaDesign protocol to change a structure's
		amino acid sequence while maintaining a fixed backbone.
		Generates the structure.pdb file
		'''
		#A - Relax original structure
		pose = pose_from_pdb(filename)
		chain = pose.pdb_info().chain(1)
		scorefxn = get_fa_scorefxn()
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		Rscore_before = scorefxn(pose)
		Rpose_work = Pose()
		Rpose_lowest = Pose()
		Rscores = []
		Rscores.append(Rscore_before)
		for nstruct in range(relax_iters):
			Rpose_work.assign(pose)
			relax.apply(Rpose_work)
			Rscore_after = scorefxn(Rpose_work)
			Rscores.append(Rscore_after)
			if Rscore_after < Rscore_before:
				Rscore_before = Rscore_after
				Rpose_lowest.assign(Rpose_work)
			else:
				continue
		pose.assign(Rpose_lowest)
		RFinalScore = scorefxn(pose)
		#B - Perform fixbb RosettaDesign
		packtask = standard_packer_task(pose)
		pack = pyrosetta.rosetta.protocols.minimization_packing.PackRotamersMover(scorefxn, packtask)
		Dscore_before = 0
		Dpose_work = Pose()
		Dpose_lowest = Pose()
		Dscores = []
		Dscores.append(Dscore_before)
		for nstruct in range(design_iters):
			Dpose_work.assign(pose)
			pack.apply(Dpose_work)
			Dscore_after = scorefxn(Dpose_work)
			Dscores.append(Dscore_after)
			if Dscore_after < Dscore_before:
				Dscore_before = Dscore_after
				Dpose_lowest.assign(Dpose_work)
			else:
				continue
		pose.assign(Dpose_lowest)
		DFinalScore = scorefxn(pose)
		#C - Output Result
		pose.dump_pdb('fixbb.pdb')
		#D - Print report
		print('==================== Result Report ====================')
		print('Relax Scores:\n', Rscores)
		print('Chosen Lowest Score:', RFinalScore, '\n')
		print('Design Scores:\n', Dscores)
		print('Chosen Lowest Score:', DFinalScore, '\n')
		print('BLAST result, comparing the original structure to the designed structure:')
		RosettaDesign.BLAST(self, filename, 'fixbb.pdb')

	def flxbb(self, filename, relax_iters, design_iters):
		'''
		Performs the RosettaDesign protocol to change a structure's
		amino acid sequence while allowing for a flexible backbone.
		Generates the structure.pdb file
		'''
		#A - Relax original structure
		pose = pose_from_pdb(filename)
		chain = pose.pdb_info().chain(1)
		scorefxn = get_fa_scorefxn()
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		Rscore_before = scorefxn(pose)
		Rpose_work = Pose()
		Rpose_lowest = Pose()
		Rscores = []
		Rscores.append(Rscore_before)
		for nstruct in range(relax_iters):
			Rpose_work.assign(pose)
			relax.apply(Rpose_work)
			Rscore_after = scorefxn(Rpose_work)
			Rscores.append(Rscore_after)
			if Rscore_after < Rscore_before:
				Rscore_before = Rscore_after
				Rpose_lowest.assign(Rpose_work)
			else:
				continue
		pose.assign(Rpose_lowest)
		RFinalScore = scorefxn(pose)
		#B - Perform flxbb RosettaDesign
		task = pyrosetta.rosetta.core.pack.task.TaskFactory()
		movemap = MoveMap()
		movemap.set_bb(True)
		movemap.set_chi(True)
		mover = pyrosetta.rosetta.protocols.denovo_design.movers.FastDesign()
		mover.set_task_factory(task)
		mover.set_movemap(movemap)
		mover.set_scorefxn(scorefxn)
		Dscore_before = 0
		Dpose_work = Pose()
		Dpose_lowest = Pose()
		Dscores = []
		Dscores.append(Dscore_before)
		for nstruct in range(design_iters):
			Dpose_work.assign(pose)
			mover.apply(Dpose_work)
			Dscore_after = scorefxn(Dpose_work)
			Dscores.append(Dscore_after)
			if Dscore_after < Dscore_before:
				Dscore_before = Dscore_after
				Dpose_lowest.assign(Dpose_work)
			else:
				continue
		pose.assign(Dpose_lowest)
		DFinalScore = scorefxn(pose)
		#C - Output Result
		pose.dump_pdb('flxbb.pdb')
		#D - Print report
		print('==================== Result Report ====================')
		print('Relax Scores:\n', Rscores)
		print('Chosen Lowest Score:', RFinalScore, '\n')
		print('Design Scores:\n', Dscores)
		print('Chosen Lowest Score:', DFinalScore, '\n')
		print('BLAST result, comparing the original structure to the designed structure:')
		RosettaDesign.BLAST(self, filename, 'flxbb.pdb')

	def BDR(self, filename, refine_iters):
		#A - Generate constraints file
		structure = Bio.PDB.PDBParser(QUIET=True).get_structure('{}'.format(filename), filename)
		length = len(structure[0]['A'])
		ppb = Bio.PDB.Polypeptide.PPBuilder()
		Type = ppb.build_peptides(structure, aa_only=False)
		model = Type
		chain = model[0]
		CST = []
		CST.append(0.0)
		for aa in range(1, length+1):
			try:
				residue1 = chain[0]
				residue2 = chain[aa]
				atom1 = residue1['CA']
				atom2 = residue2['CA']
				CST.append(atom1-atom2)
			except:
				pass
		atom = 1
		for cst in CST:
			line = 'AtomPair CA 1 CA '+str(atom)+' GAUSSIANFUNC '+str(cst)+' 1.0\n'
			thefile = open('structure.constraints', 'a')
			thefile.write(line)
			thefile.close()
			atom += 1
		#B - Generate blueprint file (remodeling only large loops)
		dssp = Bio.PDB.DSSP(structure[0], filename)
		SS = []
		SEQ = []
		for ss in dssp:
			if ss[2] == 'G' or ss[2] == 'H' or ss[2] == 'I':
				rename = 'HX'
			elif ss[2] == 'B' or ss[2] == 'E':
				rename = 'EX'
			else:
				rename = 'LX'
			SS.append(rename)
			SEQ.append(ss[1])
		buf = []
		items = []
		l_seen = 0
		for count, (ss, aa) in enumerate(zip(SS, SEQ), 1):
			buf.append((count, aa, ss))
			if 'LX' in {ss, aa}:
				l_seen += 1
				if l_seen >= 3:
					for count, aa, ss in buf:
						line = [str(count), aa, ss, '.' if ss in {'HX', 'EX'} else 'R']
						line = ' '.join(line)
						items.append(line)
					buf.clear()
			else:
				l_seen = 0
				for count, aa, ss in buf:
					line = [str(count), aa, ss, '.']
					line = ' '.join(line)
					items.append(line)
				buf.clear()
		if int(items[-1].split()[0]) != count:
			line = [str(count), aa, ss, '.']
			line = ' '.join(line)
			items.append(line)
		blueprint = open('structure.blueprint', 'a')
		for line in items:
			blueprint.write(line+'\n')
		blueprint.close()
		#C - Run BluePrint mover
		pose = pose_from_pdb(filename)
		scorefxn = get_fa_scorefxn()
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		secstr = pyrosetta.rosetta.protocols.fldsgn.potentials.SetSecStructEnergies(scorefxn,'structure.blueprint', True)
		secstr.apply(pose)
		BDR = pyrosetta.rosetta.protocols.fldsgn.BluePrintBDR()
		BDR.num_fragpick(200)
		BDR.use_fullmer(True)
		BDR.use_sequence_bias(False)
		BDR.max_linear_chainbreak(0.07)
		BDR.ss_from_blueprint(True)
		BDR.dump_pdb_when_fail('')
		BDR.set_constraints_NtoC(-1.0)
		BDR.use_abego_bias(True)
		#BDR.set_constraint_file('structure.constraints')
		BDR.set_blueprint('structure.blueprint')
		Dscore_before = 0
		Dpose_work = Pose()
		Dpose_lowest = Pose()
		Dscores = []
		Dscores.append(Dscore_before)
		for nstruct in range(refine_iters):
			Dpose_work.assign(pose)
			BDR.apply(Dpose_work)
			relax.apply(Dpose_work)
			Dscore_after = scorefxn(Dpose_work)
			Dscores.append(Dscore_after)
			if Dscore_after < Dscore_before:
				Dscore_before = Dscore_after
				Dpose_lowest.assign(Dpose_work)
			else:
				continue
		pose.assign(Dpose_lowest)
		DFinalScore = scorefxn(pose)
		#D - Output Result
		pose.dump_pdb('remodel.pdb')
		os.remove('structure.constraints')
		os.remove('structure.blueprint')
		#E - Print report
		print('==================== Result Report ====================')
		print('Design Scores:\n', Dscores)
		print('Chosen Lowest Score:', DFinalScore, '\n')

	def Refine(self, filename, refine_iters):
		os.system('cp {} temp.pdb'.format(filename))
		Mutate = [1]
		while Mutate != []:
			inputfile = 'temp.pdb'
			parser = Bio.PDB.PDBParser()
			structure = parser.get_structure('{}'.format(inputfile), inputfile)
			dssp = Bio.PDB.DSSP(structure[0], inputfile, acc_array='Wilke')
			sasalist = []
			for x in dssp:
				if x[1] == 'A':
					sasa = 129*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'V':
					sasa = 174*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'I':
					sasa = 197*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'L':
					sasa = 201*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'M':
					sasa = 224*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'P':
					sasa = 159*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'Y':
					sasa = 263*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'F':
					sasa = 240*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'W':
					sasa = 285*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'R':
					sasa = 274*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'N':
					sasa = 195*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'C':
					sasa = 167*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'Q':
					sasa = 225*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'E':
					sasa = 223*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'G':
					sasa = 104*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'H':
					sasa = 224*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'K':
					sasa = 236*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'S':
					sasa = 155*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'T':
					sasa = 172*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				elif x[1] == 'D':
					sasa = 193*(x[3])
					if sasa <= 25:
						sasa = 'C'
					elif 25 < sasa < 40:
						sasa = 'B'
					elif sasa >= 40:
						sasa = 'S'
				if x[2] == 'G' or x[2] == 'H' or x[2] == 'I':
					ss = 'H'
				elif x[2] == 'B' or x[2] == 'E':
					ss = 'S'
				elif x[2] == 'S' or x[2] == 'T' or x[2] == '-':
					ss = 'L'
				sasalist.append((x[0], x[1], ss, sasa))
			Resids = []
			SecStr = []
			SASAps = []
			MutPos = []
			Mutate = []
			for n, r, s, a in sasalist:
				if a == 'S' and s == 'L' and (	   r == 'P' or r == 'G' 
								or r == 'N' or r == 'Q'
								or r == 'S' or r == 'T'
								or r == 'D' or r == 'E'
								or r == 'R' or r == 'K'
								or r == 'H'):
					MutPos.append(' ')
				elif a=='B' and s=='L' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'F' or r == 'Y'
								or r == 'W' or r == 'G'
								or r == 'N' or r == 'Q'
								or r == 'S' or r == 'T'
								or r == 'P' or r == 'D'
								or r == 'E' or r == 'K'
								or r == 'R'):
					MutPos.append(' ')
				elif a=='C' and s=='L' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'P' or r == 'F'
								or r == 'W' or r == 'M'):
					MutPos.append(' ')
				elif a=='S' and s=='H' and (	   r == 'Q' or r == 'E'
								or r == 'K' or r == 'H'):
					MutPos.append(' ')
				elif a=='B' and s=='H' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'W' or r == 'Q'
								or r == 'E' or r == 'K'
								or r == 'F' or r == 'M'):
					MutPos.append(' ')
				elif a=='C' and s=='H' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'F' or r == 'W'
								or r == 'M'):
					MutPos.append(' ')
				elif a=='S' and s=='S' and (	   r == 'Q' or r == 'T'
								or r == 'Y'):
					MutPos.append(' ')
				elif a=='B' and s=='S' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'F' or r == 'Y'
								or r == 'W' or r == 'Q'
								or r == 'T' or r == 'M'):
					MutPos.append(' ')
				elif a=='C' and s=='S' and (	   r == 'A' or r == 'V'
								or r == 'I' or r == 'L'
								or r == 'F' or r == 'W'
								or r == 'M'):
					MutPos.append(' ')
				else:
					MutPos.append('*')
					Mutate.append((n, r, s, a))		
				Resids.append(r)
				SASAps.append(a)
				SecStr.append(s)
			Resids=''.join(Resids)
			SASAps=''.join(SASAps)
			MutPos=''.join(MutPos)
			SecStr=''.join(SecStr)
			print('{}\n{}\n{}\n{}'.format(Resids, SecStr, SASAps, MutPos))
			pose = pose_from_pdb(inputfile)
			scorefxn = get_fa_scorefxn()
			relax = pyrosetta.rosetta.protocols.relax.FastRelax()
			relax.set_scorefxn(scorefxn)
			ideal = pyrosetta.rosetta.protocols.idealize.IdealizeMover()
			resfile = open('structure.res', 'a')
			resfile.write('NATRO\nSTART\n')
			for n, r, a, s in Mutate:
				if s == 'S' and a == 'L':
					line = '{} A PIKAA PGNQSTDERKH\n'.format(n)
					resfile.write(line)
				elif s == 'S' and a == 'H':
					line = '{} A PIKAA QEKH\n'.format(n)
					resfile.write(line)
				elif s == 'S' and a == 'S':
					line = '{} A PIKAA QTY\n'.format(n)
					resfile.write(line)
				elif s == 'B' and a == 'L':
					line = '{} A PIKAA AVILFYWGNQSTPDEKR\n'.format(n)
					resfile.write(line)
				elif s == 'B' and a == 'H':
					line = '{} A PIKAA AVILWQEKFM\n'.format(n)
					resfile.write(line)
				elif s == 'B' and a == 'S':
					line = '{} A PIKAA AVILFYWQTM\n'.format(n)
					resfile.write(line)
				elif s == 'C' and a == 'L':
					line = '{} A PIKAA AVILPFWM\n'.format(n)
					resfile.write(line)
				elif s == 'C' and a == 'H':
					line = '{} A PIKAA AVILFWM\n'.format(n)
					resfile.write(line)
				elif s == 'C' and a == 'S':
					line = '{} A PIKAA AVILFWM\n'.format(n)
					resfile.write(line)
			resfile.close()
			pack = standard_packer_task(pose)
			pack.temporarily_fix_everything()
			pyrosetta.rosetta.core.pack.task.parse_resfile(pose, pack, 'structure.res')
			for n, r, s, a in Mutate:
				x = pose.residue(n).name()
				if x == 'CYS:disulphide':
					continue
				else:
					pack.temporarily_set_pack_residue(n, True) 
			print(pack)
			pack = pyrosetta.rosetta.protocols.minimization_packing.PackRotamersMover(scorefxn, pack)
			Dscore_before = 0
			Dpose_work = Pose()
			Dpose_lowest = Pose()
			Dscores = []
			Dscores.append(Dscore_before)
			for nstruct in range(refine_iters):
				Dpose_work.assign(pose)
				pack.apply(Dpose_work)
				ideal.apply(Dpose_work)
				relax.apply(Dpose_work)
				Dscore_after = scorefxn(Dpose_work)
				Dscores.append(Dscore_after)
				if Dscore_after < Dscore_before:
					Dscore_before = Dscore_after
					Dpose_lowest.assign(Dpose_work)
				else:
					continue
			pose.assign(Dpose_lowest)
			DFinalScore = scorefxn(pose)
			os.remove('structure.res')
			os.remove('temp.pdb')
			pose.dump_pdb('temp.pdb')
		pose.dump_pdb('structure.pdb')
		os.remove('temp.pdb')

class MCRosettaDesign():
	'''
	This class preforms RosettaDesign either fixed backbone 
	design (fixbb) or flexible backbone design (flxbb) using
	the Monte Carlo method, generating many designed structures
	thus it is best to select the lowest scoring structure.
	'''
	def __init__(self):
		pass

	def fixbb(self, filename, kT, cycles, jobs, job_output):
		'''
		Performs fixed backbone RosettaDesign using the
		Monte Carlo method using the following sequence:
		1. Relax
		2. Fixed backbone design (by SASA layers)
		'''
		# Generate resfile
		parser = Bio.PDB.PDBParser()
		structure = parser.get_structure('{}'.format(filename), filename)
		dssp = Bio.PDB.DSSP(structure[0], filename, acc_array='Wilke')
		sasalist = []
		for x in dssp:
			if x[1] == 'A':
				sasa = 129*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'V':
				sasa = 174*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'I':
				sasa = 197*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'L':
				sasa = 201*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'M':
				sasa = 224*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'P':
				sasa = 159*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'Y':
				sasa = 263*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'F':
				sasa = 240*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'W':
				sasa = 285*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'R':
				sasa = 274*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'N':
				sasa = 195*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'C':
				sasa = 167*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'Q':
				sasa = 225*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'E':
				sasa = 223*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'G':
				sasa = 104*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'H':
				sasa = 224*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'K':
				sasa = 236*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'S':
				sasa = 155*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'T':
				sasa = 172*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'D':
				sasa = 193*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			if x[2] == 'G' or x[2] == 'H' or x[2] == 'I':
				ss = 'H'
			elif x[2] == 'B' or x[2] == 'E':
				ss = 'S'
			elif x[2] == 'S' or x[2] == 'T' or x[2] == '-':
				ss = 'L'
			sasalist.append((x[0], x[1], ss, sasa))
		resfile = open('resfile', 'a')
		resfile.write('NATRO\nSTART\n')
		for n, r, a, s in sasalist:
			if s == 'S' and a == 'L':
				line = '{} A PIKAA PGNQSTDERKH\n'.format(n)
				resfile.write(line)
			elif s == 'S' and a == 'H':
				line = '{} A PIKAA QEKH\n'.format(n)
				resfile.write(line)
			elif s == 'S' and a == 'S':
				line = '{} A PIKAA QTY\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'L':
				line = '{} A PIKAA AVILFYWGNQSTPDEKR\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'H':
				line = '{} A PIKAA AVILWQEKFM\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'S':
				line = '{} A PIKAA AVILFYWQTM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'L':
				line = '{} A PIKAA AVILPFWM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'H':
				line = '{} A PIKAA AVILFWM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'S':
				line = '{} A PIKAA AVILFWM\n'.format(n)
				resfile.write(line)
		resfile.close()
		# RosettaDesign: Relax Fixbb, Relax
		pose = pose_from_pdb(filename)
		starting_pose = Pose()
		starting_pose.assign(pose)
		scorefxnBUH = get_fa_scorefxn()
		scorefxnBUH.set_weight(pyrosetta.rosetta.core.scoring.ScoreType.buried_unsatisfied_penalty, 1.0)
		scorefxn = get_fa_scorefxn()
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		packtask = standard_packer_task(pose)
		pyrosetta.rosetta.core.pack.task.parse_resfile(pose, packtask, 'resfile')
		fixbb = pyrosetta.rosetta.protocols.minimization_packing.PackRotamersMover(scorefxnBUH, packtask)
		sequence = SequenceMover()
		sequence.add_mover(relax)
		sequence.add_mover(fixbb)
		sequence.add_mover(relax)
		mc = MonteCarlo(pose, scorefxn, kT)
		trial = TrialMover(sequence, mc)
		RosettaDesign = RepeatMover(trial, cycles)
		job = PyJobDistributor(job_output, jobs, scorefxn)
		job.native_pose = starting_pose
		while not job.job_complete:
			pose.assign(starting_pose)
			mc.reset(pose)
			RosettaDesign.apply(pose)
			mc.recover_low(pose)
			job.output_decoy(pose)
		os.remove('resfile')

	def flxbb(self, filename, kT, cycles, jobs, job_output):
		'''
		Performs flexible backbone RosettaDesign using the
		Monte Carlo method using the following sequence:
		1. Relax
		2. BluePrintBDR loop remodeling
		3. Flexible backbone design (by SASA layers)
		4. Idealise
		5. Relax
		'''
		# Generate blueprint file
		structure = Bio.PDB.PDBParser(QUIET=True).get_structure('{}'.format(filename), filename)
		dssp = Bio.PDB.DSSP(structure[0], filename)
		SS = []
		SEQ = []
		for ss in dssp:
			if ss[2] == 'G' or ss[2] == 'H' or ss[2] == 'I':
				rename = 'HX'
			elif ss[2] == 'B' or ss[2] == 'E':
				rename = 'EX'
			else:
				rename = 'LX'
			SS.append(rename)
			SEQ.append(ss[1])
		buf = []
		items = []
		l_seen = 0
		for count, (ss, aa) in enumerate(zip(SS, SEQ), 1):
			buf.append((count, aa, ss))
			if 'LX' in {ss, aa}:
				l_seen += 1
				if l_seen >= 3:
					for count, aa, ss in buf:
						line = [str(count), aa, ss, '.' if ss in {'HX', 'EX'} else 'R']
						line = ' '.join(line)
						items.append(line)
					buf.clear()
			else:
				l_seen = 0
				for count, aa, ss in buf:
					line = [str(count), aa, ss, '.']
					line = ' '.join(line)
					items.append(line)
				buf.clear()
		if int(items[-1].split()[0]) != count:
			line = [str(count), aa, ss, '.']
			line = ' '.join(line)
			items.append(line)
		blueprint = open('blueprint', 'a')
		for line in items:
			blueprint.write(line+'\n')
		blueprint.close()
		# Generate resfile
		parser = Bio.PDB.PDBParser()
		structure = parser.get_structure('{}'.format(filename), filename)
		dssp = Bio.PDB.DSSP(structure[0], filename, acc_array='Wilke')
		sasalist = []
		for x in dssp:
			if x[1] == 'A':
				sasa = 129*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'V':
				sasa = 174*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'I':
				sasa = 197*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'L':
				sasa = 201*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'M':
				sasa = 224*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'P':
				sasa = 159*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'Y':
				sasa = 263*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'F':
				sasa = 240*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'W':
				sasa = 285*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'R':
				sasa = 274*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'N':
				sasa = 195*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'C':
				sasa = 167*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'Q':
				sasa = 225*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'E':
				sasa = 223*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'G':
				sasa = 104*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'H':
				sasa = 224*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'K':
				sasa = 236*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'S':
				sasa = 155*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'T':
				sasa = 172*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			elif x[1] == 'D':
				sasa = 193*(x[3])
				if sasa <= 25:
					sasa = 'C'
				elif 25 < sasa < 40:
					sasa = 'B'
				elif sasa >= 40:
					sasa = 'S'
			if x[2] == 'G' or x[2] == 'H' or x[2] == 'I':
				ss = 'H'
			elif x[2] == 'B' or x[2] == 'E':
				ss = 'S'
			elif x[2] == 'S' or x[2] == 'T' or x[2] == '-':
				ss = 'L'
			sasalist.append((x[0], x[1], ss, sasa))
		resfile = open('resfile', 'a')
		resfile.write('NATRO\nSTART\n')
		for n, r, a, s in sasalist:
			if s == 'S' and a == 'L':
				line = '{} A PIKAA PGNQSTDERKH\n'.format(n)
				resfile.write(line)
			elif s == 'S' and a == 'H':
				line = '{} A PIKAA QEKH\n'.format(n)
				resfile.write(line)
			elif s == 'S' and a == 'S':
				line = '{} A PIKAA QTY\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'L':
				line = '{} A PIKAA AVILFYWGNQSTPDEKR\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'H':
				line = '{} A PIKAA AVILWQEKFM\n'.format(n)
				resfile.write(line)
			elif s == 'B' and a == 'S':
				line = '{} A PIKAA AVILFYWQTM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'L':
				line = '{} A PIKAA AVILPFWM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'H':
				line = '{} A PIKAA AVILFWM\n'.format(n)
				resfile.write(line)
			elif s == 'C' and a == 'S':
				line = '{} A PIKAA AVILFWM\n'.format(n)
				resfile.write(line)
		resfile.close()
		# RosettaDesign: Relax, BluePrintBDR, Flxbb, Idealize, Relax
		pose = pose_from_pdb(filename)
		starting_pose = Pose()
		starting_pose.assign(pose)
		scorefxnBUH = get_fa_scorefxn()
		scorefxnBUH.set_weight(pyrosetta.rosetta.core.scoring.ScoreType.buried_unsatisfied_penalty, 1.0)
		scorefxn = get_fa_scorefxn()
		relax = pyrosetta.rosetta.protocols.relax.FastRelax()
		relax.set_scorefxn(scorefxn)
		BDR = pyrosetta.rosetta.protocols.fldsgn.BluePrintBDR()
		BDR.num_fragpick(200)
		BDR.use_fullmer(True)
		BDR.use_sequence_bias(False)
		BDR.max_linear_chainbreak(0.07)
		BDR.ss_from_blueprint(True)
		BDR.dump_pdb_when_fail('')
		BDR.set_constraints_NtoC(-1.0)
		BDR.use_abego_bias(True)
		BDR.set_blueprint('blueprint')
		resfile = rosetta.core.pack.task.operation.ReadResfile('resfile')
		task = pyrosetta.rosetta.core.pack.task.TaskFactory()
		task.push_back(resfile)
		movemap = MoveMap()
		movemap.set_bb(True)
		movemap.set_chi(True)
		flxbb = pyrosetta.rosetta.protocols.denovo_design.movers.FastDesign()
		flxbb.set_task_factory(task)
		flxbb.set_movemap(movemap)
		flxbb.set_scorefxn(scorefxnBUH)
		ideal = pyrosetta.rosetta.protocols.idealize.IdealizeMover()
		sequence = SequenceMover()
		sequence.add_mover(relax)
		sequence.add_mover(BDR)
		sequence.add_mover(flxbb)
		sequence.add_mover(ideal)
		sequence.add_mover(relax)
		mc = MonteCarlo(pose, scorefxn, kT)
		trial = TrialMover(sequence, mc)
		RosettaDesign = RepeatMover(trial, cycles)
		job = PyJobDistributor(job_output, jobs, scorefxn)
		job.native_pose = starting_pose
		while not job.job_complete:
			pose.assign(starting_pose)
			mc.reset(pose)
			RosettaDesign.apply(pose)
			mc.recover_low(pose)
			job.output_decoy(pose)
		os.remove('blueprint')
		os.remove('resfile')

def Fragments(filename):
	'''
	Submits the pose to the Robetta server
	(http://www.robetta.org) for fragment generation that are
	used for the Abinitio folding simulation. Then measures the
	RMSD for each fragment at each position and chooses the
	lowest RMSD. Then averages out the lowest RMSDs. Then plots
	the lowest RMSD fragment for each positon.
	Generates the 3-mer file, the 9-mer file, the PsiPred file,
	the RMSD vs Position PDF plot with the averaged fragment
	RMSD printed in the plot
	'''
	#Make the 3-mer and 9-mer fragment files and the PSIPRED file using the Robetta server
	pose = pose_from_pdb(filename)
	sequence = pose.sequence()
	#Post
	web = requests.get('http://www.robetta.org/fragmentsubmit.jsp')
	payload = {
		'UserName':'ac.research',
		'Email':'',
		'Notes':'structure',
		'Sequence':sequence,
		'Fasta':'',
		'Code':'',
		'ChemicalShifts':'',
		'NoeConstraints':'',
		'DipolarConstraints':'',
		'type':'submit'
	}
	session = requests.session()
	response = session.post('http://www.robetta.org/fragmentsubmit.jsp', data=payload , files=dict(foo='bar'))		
	for line in response:
		line = line.decode()
		if re.search('<a href="(fragmentqueue.jsp\?id=[0-9].*)">' , line):
			JobID = re.findall('<a href="(fragmentqueue.jsp\?id=[0-9].*)">' , line)
	JobURL = 'http://www.robetta.org/' + JobID[0]
	#Check
	ID = JobID[0].split('=')
	print('Job ID: ' + str(ID[1]))
	while True:
		Job = urllib.request.urlopen(JobURL)
		jobdata = bs4.BeautifulSoup(Job , 'lxml')
		status = jobdata.find('td', string='Status: ').find_next().text
		if status == 'Complete':
			print(datetime.datetime.now().strftime('%d %B %Y @ %H:%M') , 'Status:' , status)
			break
		else:
			print(datetime.datetime.now().strftime('%d %B %Y @ %H:%M') , 'Status:' , status)
			time.sleep(1800)
			continue
	#Download
	sequence = pose.sequence()
	fasta = open('structure.fasta' , 'w')
	fasta.write(sequence)
	fasta.close()
	time.sleep(1)
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/aat000_03_05.200_v1_3')
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/aat000_09_05.200_v1_3')
	os.system('wget http://www.robetta.org/downloads/fragments/' + str(ID[1])  + '/t000_.psipred_ss2')
	os.rename('aat000_03_05.200_v1_3' , 'frags.200.3mers')
	os.rename('aat000_09_05.200_v1_3' , 'frags.200.9mers')
	os.rename('t000_.psipred_ss2' , 'pre.psipred.ss2')
	#Calculate the best fragment's RMSD at each position
	frag = open('frags.200.9mers' , 'r')
	rmsd = open('temp.dat' , 'w')
	for line in frag:
		if line.lstrip().startswith('position:'):
			line = line.split()
			size = line[1]
	frag.close()
	count = 0
	for x in range (int(size)):
		count +=1
		#Get the pose and make a copy of it to apply changes to
		pose_copy = pyrosetta.Pose()
		pose_copy.assign(pose)
		#Setup frame list
		frames = pyrosetta.rosetta.core.fragment.FrameList()
		#Setup the 9-mer fragment (9-mer is better than 3-mer for this analysis)
		fragset = pyrosetta.rosetta.core.fragment.ConstantLengthFragSet(9)
		fragset.read_fragment_file('frags.200.9mers')
		fragset.frames(count , frames)
		#Setup the MoveMap
		movemap = MoveMap()
		movemap.set_bb(True)
		#Setup and apply the fragment inserting mover
		for frame in frames:
			for frag_num in range( 1 , frame.nr_frags() + 1 ):
				frame.apply(movemap , frag_num , pose_copy)
				#Measure the RMSD difference between the original pose and the new changed pose (the copy)
				RMSD = rosetta.core.scoring.CA_rmsd(pose , pose_copy)
				print(RMSD , '\t' , count)
				rmsd.write(str(RMSD) + '\t' + str(count) + '\n')
				#Reset the copy pose to original pose
				pose_copy.assign(pose)
	rmsd.close()
	#Analyse the RMSD file to get the lowest RMSD for each position
	data = open('RMSDvsPosition.dat' , 'w')
	lowest = {} 				#Mapping group number -> lowest value found
	for line in open('temp.dat'):
		parts = line.split()
		if len(parts) != 2:		#Only lines with two items on it
			continue
		first = float(parts[0])
		second = int(parts[1])
		if first == 0: 			#Skip line with 0.0 RMSD (this is an error from the 9-mer fragment file). I don't know why it happens
			continue
		if second not in lowest:
			lowest[second] = first
		else:
			if first < lowest[second]:
				lowest[second] = first
	for position, rmsd in lowest.items():
		#print(str(rmsd) + '\t' + str(position))
		data.write(str(position) + '\t' + str(rmsd) + '\n')
	data.close()
	#Calculate the average RMSD of the fragments
	data = open('RMSDvsPosition.dat' , 'r')
	value = 0
	for line in data:
		line = line.split()
		RMSD = float(line[1])
		value = value + RMSD
		count = int(line[0])
	Average_RMSD = round(value / count , 2)
	#Plot the results
	gnuplot = open('gnuplot_sets' , 'w')
	gnuplot.write("""
	reset\n
	set terminal postscript\n
	set output './plot_frag.pdf'\n
	set encoding iso_8859_1\n
	set term post eps enh color\n
	set xlabel 'Position'\n
	set ylabel 'RMSD (\\305)'\n
	set yrange [0:]\n
	set xrange [0:]\n
	set xtics auto\n
	set xtics rotate\n
	set grid front\n
	unset grid\n
	set title 'Fragment Quality'\n
	set key off\n
	set boxwidth 0.5\n
	set style fill solid\n
	set label 'Average RMSD = {}' at graph 0.01 , graph 0.95 tc lt 7 font 'curior 12'\n
	plot 'RMSDvsPosition.dat' with boxes\n
	exit
	""".format(str(Average_RMSD)))
	gnuplot.close()
	os.system('gnuplot < gnuplot_sets')
	os.remove('gnuplot_sets')
	os.remove('temp.dat')
	return(Average_RMSD)

def CSTMax(filename):
	'''
	find the minimum and maximum range of the constraints
	values of a dataset
	'''
	maxline = []
	data = open(filename, 'r')
	next(data)
	for line in data:
		line = line.strip().split(';')
		cst = []
		count = 1
		for item in line:
			if count < 450:
				count += 3
				cst.append(float(line[count]))
		maxline.append(max(cst))
	maximum = max(maxline)
	return(maximum)

def FoldPDB_PS(data):
	'''
	Fold a primary structure using the phi and psi torsion
	angles Generates the Backbone.pdb file
	'''
	#Generate a pose
	size = int(len(data[0]))
	Vs = list()
	for numb in range(size):
		Vs.append('V')
	sequence = ''.join(Vs)
	pose = pose_from_sequence(sequence)
	#Isolate each angle and constraint
	PHI = data[0]
	PSI = data[1]
	count = 1
	#Move amino acid angles
	for P, S in zip(PHI, PSI):
		pose.set_phi(count, float(P))
		pose.set_psi(count, float(S))
		count += 1
	atom = 1
	#Run FastRelax
	scorefxn = get_fa_scorefxn()
	relax = pyrosetta.rosetta.protocols.relax.FastRelax(scorefxn)
	relax.apply(pose)
	pose.dump_pdb('Backbone.pdb')

def FoldPDB_PSC(data):
	'''
	Fold a primary structure using the phi and psi torsion
	angles as well as the CA atom constraints. Generates
	the Backbone.pdb file
	'''
	#Generate a pose
	size = int(len(data[0]))
	Vs = list()
	for numb in range(size):
		Vs.append('V')
	sequence = ''.join(Vs)
	pose = pose_from_sequence(sequence)
	#Isolate each angle and constraint
	PHI = data[0]
	PSI = data[1]
	CST = data[2]
	count = 1
	#Move amino acid angles
	for P, S in zip(PHI, PSI):
		pose.set_phi(count, float(P))
		pose.set_psi(count, float(S))
		count += 1
	atom = 1
	#Write constraints file
	for cst in CST:
		line = 'AtomPair CA 1 CA '+str(atom)+' GAUSSIANFUNC '+str(cst)+' 1.0\n'
		thefile = open('constraints.cst', 'a')
		thefile.write(line)
		thefile.close()
		atom += 1
	#Add constraints option to pose
	constraints = pyrosetta.rosetta.protocols.constraint_movers.ConstraintSetMover()
	constraints.constraint_file('constraints.cst')
	constraints.add_constraints(True)
	constraints.apply(pose)
	#Setup score function with weight on only atom_pair_constraint
	scorefxnCST = ScoreFunction()
	scorefxnCST.set_weight(pyrosetta.rosetta.core.scoring.ScoreType.atom_pair_constraint, 1.0)
	#Setup constraint relax to bring atoms together
	relaxCST = pyrosetta.rosetta.protocols.relax.FastRelax()
	relaxCST.set_scorefxn(scorefxnCST)
	relaxCST.constrain_relax_to_start_coords(True)
	relaxCST.constrain_coords(True)
	#Setup normal FastRelax with constraints
	scorefxn = get_fa_scorefxn()
	relaxC = pyrosetta.rosetta.protocols.relax.FastRelax()
	relaxC.set_scorefxn(scorefxn)
	relaxC.constrain_relax_to_start_coords(True)
	relaxC.constrain_coords(True)
	#Setup normal FastRelax without constraints
	relax = pyrosetta.rosetta.protocols.relax.FastRelax()
	relax.set_scorefxn(scorefxn)
	#Run Relaxations
#	relaxCST.apply(pose)	#only brings structure together
	relaxC.apply(pose)		#Best on its own
#	relax.apply(pose)		#Best on its own
	pose.dump_pdb('Backbone.pdb')
	os.remove('constraints.cst')

def DCGAN_PS(choice, filename):
	'''
	A Convolutional Generative Adverserial Neural Network that will learn the structure of
	ideal proteins given their phi, psi angles (the dataPS.csv dataset).
	Then it generates novel angles and from random noise that will fold
	into a novel protein backbone.
	'''
	# Import data
	data = pd.read_csv(filename, ';')
	# Convert data into numpy arrays
	phi = data[data.columns[2::2]].values
	psi = data[data.columns[3::2]].values
	# MinMax scaling
	phi /= 360
	psi /= 360
	# Make the tensor - shape (examples, residues, 2 channels 3 P S )
	X = np.array([phi, psi])	# Shape = (2, 82900, 150)
	X = np.swapaxes(X, 0, 2)	# Change shape to (150, 82900, 2)
	X = np.swapaxes(X, 0, 1)	# Change shape to (82900, 150, 2)
	#Network values
	shape = (150, 2)
	latent = 100
	batchs = 32
	epochs = 3
	#Discriminator
	D = keras.models.Sequential()
	D.add(keras.layers.Conv1D(32, kernel_size=3, input_shape=shape))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(64, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(128, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(256, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Flatten())
	D.add(keras.layers.Dense(1, activation='sigmoid'))
	D.summary()
	#Generator
	G = keras.models.Sequential()
	G.add(keras.layers.Dense(79*3, activation='relu', input_dim=latent))
	G.add(keras.layers.Reshape((79, 3)))
	G.add(keras.layers.Conv1D(128, kernel_size=3))
	G.add(keras.layers.Activation('relu'))
	G.add(keras.layers.UpSampling1D())
	G.add(keras.layers.Conv1D(64, kernel_size=3))
	G.add(keras.layers.Activation('relu'))
	G.add(keras.layers.Conv1D(2, kernel_size=3))
	G.add(keras.layers.Activation('tanh'))
	G.summary()
	#Discriminator Model
	DM = keras.models.Sequential()
	DM.add(D)
	DM.compile(optimizer=keras.optimizers.Adam(0.001), loss='binary_crossentropy', metrics=['accuracy'])
	#Adversarial Model
	AM = keras.models.Sequential()
	AM.add(G)
	AM.add(D)
	AM.compile(optimizer=keras.optimizers.Adam(0.001), loss='binary_crossentropy', metrics=['accuracy'])
	if choice == 'train':
		#Training
		for epoch in range(epochs):
			#Generate a fake structures
			real = X[np.random.randint(0, X.shape[0], size=batchs)]
			noise = np.random.uniform(0.0, 1.0, size=[batchs, 100])
			fake = G.predict(noise)
			#Train discriminator
			x = np.concatenate((real, fake))
			y = np.ones([2*batchs, 1])
			y[batchs:, :] = 0
			d_loss = DM.train_on_batch(x, y)
			#Train adversarial
			y = np.ones([batchs, 1])
			a_loss = AM.train_on_batch(noise, y)
			D_loss = round(float(d_loss[0]), 3)
			D_accu = round(float(d_loss[1]), 3)
			A_loss = round(float(a_loss[0]), 3)
			print('{:7} [D loss: {:.3f}, accuracy: {:.3f}] [G loss: {:.3f}]'.format(epoch, D_loss, D_accu, A_loss))
			#Save Model
			G.save_weights('weights.h5')
	elif choice == 'generate':
		#Generate
		G.load_weights('weights.h5')
		noise = np.random.normal(0.5, 0.5, (1, 100))
		gen = G.predict(noise)
		gen = gen.reshape([300])
		gen = np.ndarray.tolist(gen)
		phiout = gen[0::2]		#[start:end:step]
		psiout = gen[1::2]		#[start:end:step]
		#Re-normalise
		phiout = [x*360.0 for x in phiout]
		psiout = [x*360.0 for x in psiout]
		return(phiout, psiout)

def DCGAN_PSC(choice, filename, CSTmax):
	# Import data
	data = pd.read_csv(filename, ';')
	# Convert data into numpy arrays
	phi = data[data.columns[2::3]].values
	psi = data[data.columns[3::3]].values
	cst = data[data.columns[4::3]].values
	# MinMax scaling
	phi /= 360
	psi /= 360
	cst /= float(CSTmax)
	# Make the tensor - shape (examples, residues, 3 channels 3 P S C)
	X = np.array([phi, psi, cst])	# Shape = (3, 82900, 150)
	X = np.swapaxes(X, 0, 2)		# Change shape to (150, 82900, 3)
	X = np.swapaxes(X, 0, 1)		# Change shape to (82900, 150, 3)
	#Network values
	shape = (150, 3)
	latent = 100
	batchs = 32
	epochs = 3
	#Discriminator
	D = keras.models.Sequential()
	D.add(keras.layers.Conv1D(32, kernel_size=3, input_shape=shape))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(64, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(128, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Conv1D(256, kernel_size=3))
	D.add(keras.layers.LeakyReLU(alpha=0.2))
	D.add(keras.layers.Flatten())
	D.add(keras.layers.Dense(1, activation='sigmoid'))
	D.summary()
	#Generator
	G = keras.models.Sequential()
	G.add(keras.layers.Dense(79*3, activation='relu', input_dim=latent))
	G.add(keras.layers.Reshape((79, 3)))
	G.add(keras.layers.Conv1D(128, kernel_size=3))
	G.add(keras.layers.Activation('relu'))
	G.add(keras.layers.UpSampling1D())
	G.add(keras.layers.Conv1D(64, kernel_size=3))
	G.add(keras.layers.Activation('relu'))
	G.add(keras.layers.Conv1D(3, kernel_size=3))
	G.add(keras.layers.Activation('tanh'))
	G.summary()
	#Discriminator Model
	DM = keras.models.Sequential()
	DM.add(D)
	DM.compile(optimizer=keras.optimizers.Adam(0.001), loss='binary_crossentropy', metrics=['accuracy'])
	#Adversarial Model
	AM = keras.models.Sequential()
	AM.add(G)
	AM.add(D)
	AM.compile(optimizer=keras.optimizers.Adam(0.001), loss='binary_crossentropy', metrics=['accuracy'])
	if choice == 'train':
		#Training
		for epoch in range(epochs):
			#Generate a fake structures
			real = X[np.random.randint(0, X.shape[0], size=batchs)]
			noise = np.random.uniform(0.0, 1.0, size=[batchs, 100])
			fake = G.predict(noise)
			#Train discriminator
			x = np.concatenate((real, fake))
			y = np.ones([2*batchs, 1])
			y[batchs:, :] = 0
			d_loss = DM.train_on_batch(x, y)
			#Train adversarial
			y = np.ones([batchs, 1])
			a_loss = AM.train_on_batch(noise, y)
			D_loss = round(float(d_loss[0]), 3)
			D_accu = round(float(d_loss[1]), 3)
			A_loss = round(float(a_loss[0]), 3)
			print('{:7} [D loss: {:.3f}, accuracy: {:.3f}] [G loss: {:.3f}]'.format(epoch, D_loss, D_accu, A_loss))
			#Save Model
			G.save_weights('weights.h5')
	elif choice == 'generate':
		#Generate
		G.load_weights('weights.h5')
		noise = np.random.normal(0.5, 0.5, (1, 100))
		gen = G.predict(noise)
		gen = gen.reshape([450])
		gen = np.ndarray.tolist(gen)
		phiout = gen[0::3]	#[start:end:step]
		psiout = gen[1::3]	#[start:end:step]
		cstout = gen[2::3]	#[start:end:step]
		#Re-normalise
		phiout = [x*360.0 for x in phiout]
		psiout = [x*360.0 for x in psiout]
		cstout = [x*float(CSTmax) for x in cstout]
		return(phiout, psiout, cstout)

def main():
	cst = CSTMax('dataset.csv')
	if args.train:
		data = DCGAN_PSC('train', 'dataset.csv', cst)
	else:
		data = DCGAN_PSC('generate', 'dataset.csv', cst)
		FoldPDB_PSC(data)
		RD = RosettaDesign()
		RD.flxbb('Backbone.pdb', 1.0, 10, 100, 'structure')
		Fragments('structure.pdb')

if __name__ == '__main__': main()



#https://github.com/hyperopt/hyperopt
#https://towardsdatascience.com/what-are-hyperparameters-and-how-to-tune-the-hyperparameters-in-a-deep-neural-network-d0604917584a
#https://machinelearningmastery.com/grid-search-hyperparameters-deep-learning-models-python-keras/
#https://github.com/automl/HpBandSter
#https://arxiv.org/abs/1807.01774
#http://www.jmlr.org/papers/volume13/bergstra12a/bergstra12a.pdf

