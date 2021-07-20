#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
import copy

from mods.FragmentData import FragmentData



# =============== variables =============== #
RE_FRAGMENT = re.compile(r"^[\s\t]*\d+[\s\t]*|[\s\t]*(?:(?:ERR)|(?:-?\d+))[\s\t]*|[\s\t]*(?:(?:ERR)|(?:-?\d+))[\s\t]*|(?:[\s\t]*\d+)+")
RE_CONNECTION = re.compile(r"^(?:[\s\t]*\d+){2}[\s\t]*$")
INDENT = "  "


# =============== classes =============== #
class FileFred:
	""" fred File class """
	def __init__(self):
		self._n_atom = 0
		self._charge = 0
		self._fragments = []
		self._connection = []
		self._parameters = {}


	@property
	def n_atom(self):
		return self._n_atom

	@property
	def charge(self):
		return self._charge

	@property
	def fragments(self):
		return self._fragments

	@property
	def n_fragment(self):
		return len(self._fragments)

	@property
	def parameters(self):
		return self._parameters

	@property
	def complete_parameters(self):
		parameters = copy.deepcopy(self._parameters)
		if "&CNTRL" in parameters["LIST_ORDER"] and \
			"Natom" in parameters.keys():
			parameters["&CNTRL"]["Natom"] = sum([len(v.atoms) for v in self._fragments])

		if "&FMOCNTRL" in parameters["LIST_ORDER"] and \
			"NF" in parameters.keys():
			parameters["&FMOCNTRL"]["NF"] = len(self._fragments)

		if "&FMOCNTRL" in parameters["LIST_ORDER"] and \
			"Charge" in parameters.keys():
			parameters["&CNTRL"]["Charge"] = sum([v.charge for v in self._fragments])

		if "&FMOCNTRL" in parameters["LIST_ORDER"] and \
			"AutoFrag" in parameters.keys():
			parameters["&FMOCNTRL"]["AutoFrag"] = "'OFF'"

		parameters["&FRAGMENT"] = ""
		parameters["&FRAGMENT"] += "\n".join([
			"".join(
				["{0:>8}".format(len(obj_fragment.atoms)) for obj_fragment in self._fragments[i:i+10]]
			) for i in range(0, len(self._fragments), 10)
		]) + "\n"
		parameters["&FRAGMENT"] += "\n".join([
			"".join(
				["{0:>8}".format(obj_fragment.charge) for obj_fragment in self._fragments[i:i+10]]
			) for i in range(0, len(self._fragments), 10)
		]) + "\n"
		parameters["&FRAGMENT"] += "\n".join([
			"".join(
				["{0:>8}".format(obj_fragment.bda) for obj_fragment in self._fragments[i:i+10]]
			) for i in range(0, len(self._fragments), 10)
		]) + "\n"
		parameters["&FRAGMENT"] += "\n".join([
			"\n".join([
				"".join([
					"{0:>8}".format(atom_idx) for atom_idx in obj_fragment.atoms[atom_i:atom_i+10]
				]) for atom_i in range(0, len(obj_fragment.atoms), 10)
			]) for obj_fragment in self._fragments
		]) + "\n"
		parameters["&FRAGMENT"] += "\n".join([
			"".join(
				["{0:>8}".format(i) for i in connect]
			) for connect in self._connection
		]) + "\n"

		return parameters


	def set_n_atom(self, n_atom):
		"""
		Method to set number of atoms in system

		Args:
			n_atom (int): number of atoms in system

		Returns:
			self
		"""
		self._n_atom = n_atom
		return self


	def set_charge(self, charge):
		"""
		Method to set system charge

		Args:
			charge (int): system charge

		Returns:
			self
		"""
		self._charge = charge
		return self


	def set_fragments(self, list_fragments):
		"""
		Method to set fragment object list

		Args:
			list_fragments (list): fragment object list

		Returns:
			self
		"""
		self._fragments = list_fragments
		return self


	def set_connections(self, list_connection):
		"""
		Method to set connection list

		Args:
			list_connection (list): connection list

		Returns:
			self
		"""
		self._connection = list_connection
		return self


	def set_parameters(self, parameters):
		"""
		Method to set other information

		Args:
			parameters (list): other information

		Returns:
			self
		"""
		self._parameters = parameters
		return self


	def read(self, input_file):
		"""
		Method to read .fred file

		Args:
			input_file (str): .fred file

		Returns:
			self
		"""
		with open(input_file, "r") as obj_input:
			flag_read = 0
			is_list_type = False
			group_name = None
			self._parameters = {"LIST_ORDER": []}
			for line_idx, line_val in enumerate(obj_input, 1):
				line_val = line_val.strip()

				if line_idx == 1:
					flag_read = 1

				elif "connections" in line_val.lower():
					flag_read = 2

				elif "< namelist >" in line_val.lower():
					flag_read = 3

				elif flag_read == 1 and RE_FRAGMENT.search(line_val):
					obj_fragment = FragmentData().create_from_fred_line(line_val)
					if obj_fragment.charge != "ERR":
						self._charge += obj_fragment.charge
					self._fragments.append(obj_fragment)
					self._n_atom += len(obj_fragment.atoms)

				elif flag_read == 2 and RE_CONNECTION.search(line_val):
					self._connection.append([int(x) for x in line_val.strip().split()])

				elif flag_read == 3:
					line_orig = line_val
					line_val = line_val.strip()
					if len(line_val.strip()) == 0:
						continue

					if line_val.startswith("&"):
						# start of name list
						group_name = line_val
						self._parameters["LIST_ORDER"].append(group_name)

						if group_name in ["&XYZ", "&FRAGMENT", "&FRAGPAIR"]:
							is_list_type = True
							self._parameters[group_name] = []
						else:
							is_list_type = False
							self._parameters[group_name] = {}

					elif line_val.startswith("/"):
						# end of name list
						group_name = None
						is_list_type = False
						continue

					elif is_list_type:
						# in name list of list type (order is important)
						self._parameters[group_name].append(line_orig)

					else:
						# in namelist of non-list type (order is not important)
						tmp_values = [v.strip() for v in line_val.split("=", maxsplit = 1)]
						self._parameters[group_name][tmp_values[0]] = tmp_values[1]

		return self


	def add_fragment(self, obj_fragment):
		"""
		Method to add fragment

		Args:
			obj_fragment (FragmentData object): FragmentData object

		Returns:
			self
		"""
		for fragment_idx, obj_fragment_registered in enumerate(self._fragments):
			remain_atoms = sorted(list(set(obj_fragment_registered.atoms) - set(obj_fragment.atoms)))
			obj_fragment_registered.set_atoms(remain_atoms)
			if len(obj_fragment_registered.atoms) == 0:
				self._fragments.pop(fragment_idx)

		self._n_atom += len(obj_fragment.atoms)
		self._fragments.append(obj_fragment)
		return self


	def add_connection(self, connection):
		"""
		Method to add fragment connection

		Args:
			connection (int or list): connection information

		Returns:
			self
		"""
		if isinstance(connection, int):
			for i in range(connection):
				self._connection.append(["*", "*"])
		elif isinstance(connection, list):
			self._connection.append(connection)
		return self


	def write(self, output_file, indent=INDENT):
		"""
		Method to write out file

		Args:
			output_file (str): output file
			indent (int, optional): indent length

		Returns:
			self
		"""
		tmp_fragments = sorted([[obj_fragment.min_index, obj_fragment] for obj_fragment in self._fragments], key=lambda x : x[0])
		self._fragments = [obj_fragment[1].set_fragment_index(idx) for idx, obj_fragment in enumerate(tmp_fragments, 1)]
		tmp_connection_int = sorted([x for x in self._connection if isinstance(x[0], int)], key=lambda x : x[0])
		tmp_connection_str = sorted([x for x in self._connection if isinstance(x[0], str)], key=lambda x : x[0])
		self._connection = tmp_connection_int + tmp_connection_str

		with open(output_file, "w") as obj_output:
			obj_output.write("  FNo.  | Charge | BDA | Atoms of fragment\n")
			for idx, fragment in enumerate(self._fragments, 1):
				fragment.set_fragment_index(idx)
				obj_output.write("{0:>7} |{1:>6}  |{2:>3}  |{3}\n".format(fragment.fragment_index, fragment.charge, fragment.bda, " ".join(["{0:>8}".format(x) for x in fragment.atoms])))
			obj_output.write("\n")

			obj_output.write("<< connections (ex. \"Next_fragment_atom   Prev_fragment_atom\") >>\n")
			for connection in self._connection:
				obj_output.write("{0}\n".format(" ".join(["{0:>9}".format(x) for x in connection])))
			obj_output.write("\n")

			obj_output.write("===============< namelist >===============\n")

			if "&FMOCNTRL" in self._parameters["LIST_ORDER"] and \
				"NF" in self._parameters.keys():
				self._parameters["&FMOCNTRL"]["NF"] = len(self._fragments)

			for group_name in self._parameters["LIST_ORDER"]:
				obj_output.write("{0}\n".format(group_name))
				if isinstance(self._parameters[group_name], dict):
					for parameter_name, parameter_value in self._parameters[group_name].items():
						obj_output.write("{0}{1}={2}\n".format(
							INDENT,
							parameter_name,
							parameter_value
						))
				else:
					for line_val in self._parameters[group_name]:
						obj_output.write(line_val + "\n")
				obj_output.write("/\n\n")


		return self
