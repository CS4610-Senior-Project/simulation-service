# *****************************************************************************
#  This material contains trade secrets or otherwise confidential
#  information owned by Siemens Industry Software Inc. or its
#  affiliates (collectively, "Siemens"), or its licensors. Access to
#  and use of this information is strictly limited as set forth in the
#  Customer's applicable agreements with Siemens.
# 
#  Unpublished work. Copyright 2023 Siemens
# *****************************************************************************

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import next
from builtins import zip
from builtins import str
from builtins import range
import six
from past.builtins import basestring
from builtins import object
import sys
import inspect
from functools import wraps

try:
    import afp
except:
    raise ImportError("Embedded API module 'AME' can only be used inside of the Simcenter Amesim application, e.g. in Apps; try importing 'ame_apy' instead")

if sys.version_info[0] < 3:
    import exceptions
else:
    import builtins as exceptions

import threading

import xml.etree.cElementTree as ET
import xml.sax.saxutils
from io import StringIO
import urllib.request, urllib.parse, urllib.error
import struct
import ast
import _AME

try:
    import embedded_py
    __embedded_py_available = True
except ImportError:
    print("Could not import module 'embedded_py'.")
    print("Some API functionality may not work.")
    __embedded_py_available = False

# Private utilities

def unsupported_function(func):
    """Used in case when a certain function is no more suppported. This makes the 
       method a dummy method."""
    @wraps(func)
    def decorator():
        print(f"Warning, the function '{func.__name__}' is no longer supported as of Simcenter Amesim 2210")
    return decorator

def unsupported_signature(old_signature_str):
    """Used in case when a certain argument is no more suppported. The user needs to 
       pass the complete old signature as a string. The method is still called 
       after removal of the old argument."""
    # Get the signature for Old function
    exec(f"def _old_func({old_signature_str}): pass", {}, locals())
    old_func = locals()['_old_func']
    old_signature = inspect.signature(old_func)

    def decorator(func):
        new_signature = inspect.signature(func)
        def check_type(value, fn_param: inspect.Parameter):
            if not fn_param.default is fn_param.empty:
                _default = fn_param.default
                # We do not type check if the default value is None or if the argument is none
                is_none = _default is None or value is None
    
                if not is_none and type(value) != type(_default):
                    raise TypeError
        @wraps(func)
        def newFunc(*args, **kwargs):
            try:
              # First pass
              inspect.signature(func).bind(*args, **kwargs)
      
              # Second pass (validate parameters with default values)
              args_count = len(args)
              fn_params = inspect.signature(func).parameters
      
              for arg, param in zip(args, list(fn_params)[:args_count]):
                  check_type(arg, fn_params[param])
      
              for kwarg, value in kwargs.items():
                  check_type(value, fn_params[kwarg])
                
            except TypeError:
                try:
                    # Check if the arguments match the old signature
                    ba = old_signature.bind(*args, **kwargs)

                except TypeError:
                    # They do not match the old sig, call the normal function
                    return func(*args, **kwargs)
                else:
                    # Get the removed parameters
                    diff = set(old_signature.parameters.keys()) - set(
                        new_signature.parameters.keys())
                    if(len(diff) > 1):
                        print(
                            f"Warning, function called with deprecated signature '{func.__name__}{old_signature}' : arguments {diff} are no longer supported as of Simcenter Amesim 2210.",  f"The correct signature is '{func.__name__}{inspect.signature(func)}'")
                    else:
                        print(
                            f"Warning, function called with deprecated signature '{func.__name__}{old_signature}' : argument {diff} is no longer supported as of Simcenter Amesim 2210.",  f"The correct signature is '{func.__name__}{inspect.signature(func)}'")
                    ba.apply_defaults()
                    for removed_param in diff:
                        ba.arguments.pop(removed_param)

                        return func(*ba.args, **ba.kwargs)
            else:
                return func(*args, **kwargs)

        return newFunc

    return decorator

def _IsValidBatch(batch):
   if type(batch) is Struct and hasattr(batch, TYPE) and type(batch.param) is list:
      param = batch.param
      if len(param) == 0:
         return True
      if (batch.type is BATCH.SET and (SET in param[0])) and \
      ((VALUE not in param[0]) or (ABOVE not in param[0]) or \
      (BELOW not in param[0]) or (STEP not in param[0])):
         return True
      elif batch.type is BATCH.RANGE and (SET not in param[0]) and \
      (VALUE in param[0]) and (ABOVE in param[0]) and \
      (BELOW in param[0]) and (STEP in param[0]):
         return True
   return False

def IsParamInBatch(batch,param):
   ''' To check if a particular parameter is in batch or not.

      If found returns index of parameter, else returns -1

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   no_of_params = len(batch.param)
   if no_of_params <= 0:
      return -1
   if isinstance(param, basestring):
      for i in range(0,no_of_params):
         if batch.param[i].name == param:
            return i
   elif isinstance(param, int):
      param = param - 1
      if param >= 0 and param < no_of_params:
         return param
   return -1

###############################################################################
# \brief populates xml from the given dict structure
###############################################################################
def _dict2xml_batch(d, parent=None):
   if parent is None:
     parent = ET.Element('xml')
   for key, value in list(d.items()):
     if isinstance(value, six.string_types):
       element = ET.SubElement(parent, key)
       element.text = value
     elif isinstance(value, int) or isinstance(value, float):
       element = ET.SubElement(parent, key)
       element.text = str(value)
     elif isinstance(value, dict):
       element = ET.SubElement(parent, key)
       _dict2xml_batch(value, element)
     elif isinstance(value, list):
       for item in value:
         element = ET.SubElement(parent, key)
         if isinstance(item, dict):
            _dict2xml_batch(item, element)
         else:
            element.text = str(value)
            break
     else:
       raise TypeError('Unexpected value type: {0}'.format(type(value)))
   return parent

###############################################################################
# \brief populates batch structure from xml
###############################################################################
def _xml2dict_batch(root):
   type_elem = root.find(TYPE)
   batch_type = BATCH.SET
   if type_elem.text == "RANGE":
      batch_type = BATCH.RANGE
   batch = AMECreateBatch(batch_type)
   params = root.findall('param')
   _populateParams(params, batch)
   return batch

def _populateParams(params, batch):
   for param in params:
     param_struct = _constructParam(batch, param)
     AMEBatchPutParam(batch, param_struct)

def _IsNum(number):
   try:
      num = float(number)
      return num
   except ValueError:
      return number

def _constructParam(batch, param):
   name_node = param.find(NAME)
   dict = {}
   if batch.type == "SET":
      sets_node = param.find(SET)
      sets = ast.literal_eval(sets_node.text);
      dict = {SET:sets}
   elif batch.type == "RANGE":
      value_node = _IsNum(param.find(VALUE).text)
      step_node = _IsNum(param.find(STEP).text)
      below_node = int(param.find(BELOW).text);
      above_node = int(param.find(ABOVE).text);
      dict = {VALUE : value_node, STEP : step_node, ABOVE : above_node, BELOW : below_node}
   return AMEBatchCreateParam(name_node.text, dict)

def _get_script_global_key():
    """Returns the global key for using with restrictions."""
    try:
        return threading.currentThread()._global_key
    except exceptions.AttributeError:
        _raiseThreadInitError()


def _get_current_circuit():
    """Returns the current circuit name for the API"""
    try:
        return threading.currentThread()._current_circuit
    except exceptions.AttributeError:
        _raiseThreadInitError()

def _get_current_element():
    """Returns the current element path for the API"""
    try:
        return threading.currentThread()._current_element
    except exceptions.AttributeError:
        _raiseThreadInitError()

def _get_mode(circuit):
    """Returns the current mode for the given circuit"""
    return int(afp.get(circuit + ':' + 'prop=mode'))

def _change_mode(circuit, mode):
    """Tries to set the current mode for the given circuit. Will raise
    ModeChangeError on failure."""
    try:
        afp.set(circuit + ':' + 'prop=mode', str(mode))
        new_mode = int(afp.get(circuit + ':' + 'prop=mode'))
        if new_mode != _get_mode_index(mode):
            raise RuntimeError("could only switch to mode %s" % _get_mode_name(new_mode))
    except Exception as exc:
        raise ModeChangeError('Failed to change mode for circuit "%s": %s' % (circuit, exc))

def _ensure_mode(circuit, mode):
    if _get_mode(circuit) != _get_mode_index(mode):
        _change_mode(circuit, mode)

def _ensure_mode_at_most(circuit, mode):
    if _get_mode(circuit) > _get_mode_index(mode):
        _change_mode(mode)
def _ensure_mode_at_least(circuit, mode):
    if _get_mode(circuit) < _get_mode_index(mode):
        _change_mode(circuit,mode)
_sCustomCommandCallbacks = {}
_sAMECallers = {}

def __IdGenerator():
    seed = 0
    while True:
        seed += 1
        yield str(seed)
__CustomCommandIdGenerator = __IdGenerator().__iter__()

if __embedded_py_available:
    class AMECaller(embedded_py.EPY.AppCallerInterface):
        def customUndoCommand(self, display_name, data, is_undo):
            if data in _sCustomCommandCallbacks:
                _sCustomCommandCallbacks[data](display_name, UNDO if is_undo else REDO)
        def circuitDestroyed(self):
            _sAMECallers.pop(self.getCircuitExternalName())
            afp.unregisterCaller(self)


def _RegisterAMECaller(circuit):
    if not __embedded_py_available:
        raise RuntimeError("Module embedded_py is not available.")
    if circuit not in _sAMECallers:
        caller = AMECaller()
        if isinstance(circuit, str):
            # unicode conversion to cString badly supported in Python 2
            # ensure to convert unicode into bytes before calling the registerCaller
            if sys.version_info[0] < 3:
                circuit = circuit.encode("utf8") # In Py3 need to pass a str not a bytes object
        afp.registerCaller(caller, circuit)
        _sAMECallers[circuit] = caller

def _RegisterCustomCommandCallback(circuit, callback):
    _RegisterAMECaller(circuit)
    id = next(__CustomCommandIdGenerator)
    _sCustomCommandCallbacks[id] = callback
    return id


# Error handling

def _raiseThreadInitError():
    raise RuntimeError("Use AME.Thread instead of threading.Thread if the newly created thread(or one of its children) must use the Simcenter Amesim API")

class ModeChangeError(exceptions.Exception):
    """This exception should be raised when we fail to change the mode for a circuit"""
    def __init__(self, message):
        Exception.__init__(self, message)

class DataPathError(exceptions.Exception):
    """This exception should be raised when we received an invalid data path for a request"""
    def __init__(self, message):
        Exception.__init__(self, message)

AccessError = afp.AccessError



# Utilities
standard_thread = threading.Thread
class Thread(standard_thread):
    """Use this class instead of threading.Thread if the newly created thread
       (or one of its children) must use the API."""
    def __init__(self, *args, **kwargs):
        try:
            self._current_circuit = threading.currentThread()._current_circuit
            self._current_element = threading.currentThread()._current_element
        except exceptions.AttributeError:
            _raiseThreadInitError()
        standard_thread.__init__(self, *args, **kwargs)


class AMECompLine(object):
    def __init__(self, elem, circuit):
        self.elem = elem
        self.circuit = circuit

class AMEParVar(object):
    def __init__(self, varname, elem, circuit):
        self.varname = varname
        self.elem = elem
        self.circuit = circuit




def _parse_datapath(datapath):
    if isinstance(datapath, AMEParVar):
        return datapath.varname, datapath.elem, datapath.circuit

    var_name = None
    elem_path = None
    circuit_name = None

    if datapath.count(':'):
        datapath, circuit_name = datapath.split(':')
    if datapath.count('@'):
        var_name, elem_path = datapath.split('@')
    else:
        var_name = datapath
    if elem_path is not None and len(elem_path)>0 and elem_path[0] == '#':
        elem_path = _get_current_element() + elem_path[1:]
    if not circuit_name:
        circuit_name = AMEGetActiveCircuit()
    return var_name, elem_path, circuit_name

def _make_datapath(varname, elempath, circuit):
    if elempath is None:
        return varname + ':' + circuit
    else:
        return varname + '@' + elempath + ':' + circuit

def _parse_aliaspath(aliaspath):
    if isinstance(aliaspath, AMECompLine):
        return aliaspath.elem, aliaspath.circuit

    elem_path = ''
    circuit_name = ''

    if aliaspath.count(':'):
        aliaspath, circuit_name = aliaspath.split(':')
    elem_path = aliaspath
    if elem_path is not None and len(elem_path)>0 and elem_path[0] == '#':
        elem_path = _get_current_element() + elem_path[1:]
    if not circuit_name:
        circuit_name = AMEGetActiveCircuit()
    return elem_path, circuit_name

def _get_circuit(circuit):
    if circuit is not None:
        return circuit
    return _get_current_circuit()

def _get_document(circuit):
    if circuit is None:
        circuit = _get_current_circuit()
    if "." in circuit:
        return circuit.split(".")[0]
    return circuit

def make_data_property_id(varname, elempath, circuit):
    if elempath is None:
        return circuit + ':' + varname
    else:
        return circuit + ':' + varname + '@' + elempath

def make_elem_property_id(elempath, circuit):
    return circuit + ':' + elempath

def make_circuit_property_id(circuit, prop_id):
    return circuit + ':' + prop_id

def begin_command(circuit, name):
    AMEBeginMacroCommand(name, circuit=circuit)

def end_command(circuit, name):
    afp.set(circuit + ':cmd=end_macro', name)
    AMEEndMacroCommand(name, circuit=circuit)


def _StringListFromXML(xml_str):
    return [element.text if element.text is not None else "" for element in ET.XML(xml_str).findall("ITEM")]

def _StringListToXML(str_list):
    xstr = "<LIST>"
    for str_item in str_list:
        xstr += "<ITEM>"+xml.sax.saxutils.escape(str_item)+"</ITEM>"
    xstr += "</LIST>"
    return xstr

def _NameAndPathListFromXML(tree):
   name_list = [name_list.text if name_list.text is not None else "" for name_list in ET.XML(tree).findall("submodel-name")]
   path_list = [path_list.text if path_list.text is not None else "" for path_list in ET.XML(tree).findall("submodel-path")]

   submodel_list = ()
   for i in range(0, len(name_list), 1):
      current_submodel = (name_list[i], path_list[i])
      submodel_list = submodel_list + (current_submodel,)
   return submodel_list

def _TupleListFromXML(tree):
   key_list = [key_list.text if key_list.text is not None else "" for key_list in ET.XML(tree).findall("key")]
   value_list = [value_list.text if value_list.text is not None else "" for value_list in ET.XML(tree).findall("value")]

   tuple_list = list(zip(key_list, value_list))
   return tuple_list


# Data

SKETCH_MODE     = "sketch_mode"
SUBMODEL_MODE   = "submodel_mode"
PARAMETER_MODE  = "parameter_mode"
SIMULATION_MODE = "simulation_mode"
NO_MODE         = "no_mode"
def _get_mode_name(mode_index):
    try:
        return [SKETCH_MODE, SUBMODEL_MODE, PARAMETER_MODE, SIMULATION_MODE][mode_index]
    except IndexError:
        return NO_MODE
def _get_mode_index(mode):
    try:
        return { SKETCH_MODE : 0, SUBMODEL_MODE : 1, PARAMETER_MODE : 2, SIMULATION_MODE : 3 }[mode]
    except LookupError:
        return -1

CIR_CLEAR_UNDO_STACK = "cmd=clear_undo_stack"
CIR_BEGIN_CMD = "cmd=begin_macro"
CIR_END_CMD = "cmd=end_macro"
CIR_CUSTOM_UNDO = "custom_undo"
CIR_RUN_PARAMETER = "prop=run_parameter"

UNDO = 1
REDO = 2

CONNECTION_NONE = "CONNECTION_NONE"
CONNECTION_COMPONENT = "CONNECTION_COMPONENT"
CONNECTION_LINE = "CONNECTION_LINE"
CONNECTION_PORT = "CONNECTION_PORT"

# API functions

def Data(datapath):
   """

   """
   return datapath


def Element(aliaspath):
   """

   """
   return aliaspath


def ConnectionPoint(element, port_number):
   """

   """
   return element, port_number

@unsupported_function
def GetPasswordStrList(password_list):
    pass

def SC(aliaspath):
    """
    Build an identifier for the sub-circuit of a supercomponent, which can be
    used for the circuit optional argument in other API functions.

    The supercomponent is identified by the aliaspath of its component.

    Example:

    Document: model(1).ame
        +----> Mass component:
                        aliaspath = "mass",
                        submodel = "MAS000"
        +----> Supercomponent component:
                        aliaspath = "my_sc",
                        submodel = "SC_1"
             +----> Spring component:
                            aliaspath = "my_sc.spring01",
                            submodel = "SPR000"
             +----> Zero speed component:
                            aliaspath = "my_sc.spring01",
                            submodel = "SPR000"
        +----> Line:
                   aliaspath = "signal"

    >>> AME.AMEAddComponent('th.th_solid_data', 'new_alias', (10,10), False, AME.SC('my_sc'))
	'my_sc.new_alias'

    will add a component in the supercomponent's sub-circuit, instead of the
    top-level circuit of the document.

    See also Document().
    """
    elem_path, document_id = _parse_aliaspath(aliaspath)
    return document_id + "." + elem_path

def Document(document_id):
    """
    Build an identifier for the top-level circuit of a document, that can be
    used for the circuit optional argument in other API functions.

    Example:

    Document: model(1).ame
        +----> Mass component:
                        aliaspath = "mass",
                        submodel = "MAS000"
        +----> Supercomponent component:
                        aliaspath = "my_sc",
                        submodel = "SC_1"
             +----> Spring component:
                            aliaspath = "my_sc.spring01",
                            submodel = "SPR000"
             +----> Zero speed component:
                            aliaspath = "my_sc.spring01",
                            submodel = "SPR000"
        +----> Line:
                   aliaspath = "signal"

    >>> AME.AMEAddComponent('th.th_solid_data', 'new_alias', (10,10), False, AME.Document('model(1)'))
	'new_alias'

    will add a component in the model(1) document's top-level circuit, even if
    the active circuit returned by AMEGetActiveCircuit() is a different one.

    See also SC().
    """
    return document_id

def AMEAddComponent(icon_name, alias, position, snap_ports = True, circuit=None):
    """Adds a component to the sketch of the given(or the active) circuit.

       string = AMEAddComponent(string, string, (int, int)[, bool, string])

       First string argument is the name of component icon to add.

       Second string argument is the alias to set to the component. If empty,
       an unused alias name will be automatically generated and set.

       Third int tuple argument is the position where the component has to be added
	   in the sketch, e.g. (10,15).

       Fourth bool argument is optional. If True, the component will snap and
       autoconnect to close enough ports, otherwise no automatic connection
       will be performed.

       Fifth string argument is optional. It is used to identify a different
       circuit from the active circuit in which component is to be added. See also
       SC() and Document().

       Returns alias name of the component added.

       >>> AME.AMEAddComponent('th.th_solid_data', 'new_alias', (10,10), False)
       'new_alias'
    """
    return _AME.AMEAddComponent(**locals())

def AMEAddDynamicComponent(icon_name, alias, dyn_param, position, snap_ports = True, circuit=None):
    """Adds a dynamiccomponent to the sketch of the given(or the active) circuit.

       string = AMEAddDynamicComponent(string, string, string, (int, int)[, bool, string])

       First string argument is the name of component_icon to add.

       Second string argument is the unique alias name for component. If empty,
       an unused alias name will be automatically generated and set.

       Third string argument is comma separated values for dynamic parameters of the component.

       Fourth int tuple argument is the position where component has to be added in sketch, e.g. (10,15).

       Fifth bool argument is optional. If True, the component will snap and
       autoconnect to close enough ports, otherwise no automatic connection
       will be performed.

       Sixth string argument is optional. It is used to identify a different
       circuit from the active circuit in which component is to be added. See also
       SC() and Document().

       Returns alias name of the component added.

       >>>  AME.AMEAddDynamicComponent('sig.dynamic_duplicator2', 'dyn_dup', '1,1,1',(50,30))
       'dyn_dup'
    """
    return _AME.AMEAddDynamicComponent(**locals())

def AMEAddInterfaceExportComponent(interface_type, alias, icon_text_line1, icon_text_line2, icon_text_line3, input_array, output_array, position, circuit=None):
    """Adds an interface block to the sketch of the given(or the active) circuit.

       string = AMEAddInterfaceExportComponent(string, string, string, string, string, (string), (string, string), (int, int)[, string])

       First string argument is the type of the interface to add.

       Second string argument is the unique alias name for component. If empty,
       an unused alias name will be automatically generated and set.

       Three next arguments are the text displayed in the component

       Sixth argument is a list of inputs names.

       Seventh argument is a list of outputs names.

       Eighth int tuple argument is the position where component has to be added in sketch, e.g. (10,15).

       Ninth string argument is optional. It is used to identify a different
       circuit from the active circuit in which component is to be added. See also
       SC() and Document().

       Returns alias name of the component added.

       >>>  AME.AMEAddInterfaceExportComponent('.expseu-', 'expseu_1', "Line1", "Line2", "Line3", ("input1", "input2"), ("output1", "output2", "output3"), (378,167))
       'expseu_1'
    """
    return _AME.AMEAddInterfaceExportComponent(**locals())

def AMEAddInterfaceExportComponentWithSetupFile(interface_type, alias, setup_file_path, position, circuit=None):
    """Adds an interface block to the sketch of the given(or the active) circuit.

       string = AMEAddInterfaceExportComponentWithSetupFile(string, string, string, string ,(int, int)[, string])

       First string argument is the type of the interface to add.

       Second string argument is the unique alias name for component. If empty,
       an unused alias name will be automatically generated and set.

       Three next arguments is the absolute/relative path to a setup file, used to initilize the interface.

       Fourth int tuple argument is the position where component has to be added in sketch, e.g. (10,15).

       Fifth string argument is optional. It is used to identify a different
       circuit from the active circuit in which component is to be added. See also
       SC() and Document().

       Returns the alias name of the component added.

       >>>  AME.AMEAddInterfaceExportComponent('.expseu-', 'expseu_1', 'path to the file' , (378,167))
       'expseu_1'
    """
    return _AME.AMEAddInterfaceExportComponentWithSetupFile(**locals())

def AMEGetInterfaceInputsOutputsForModel(circuit=None):
    """Returns two lists with names of interface variables set in the active circuit.
       First list contains the inputs, the second contains the outputs.
    """
    return _AME.AMEGetInterfaceInputsOutputsForModel(**locals())

def AMESetInterfaceTypeForModel(interface_type, circuit=None):
    """Sets the type of interface in the active circuit.
       Typical values : 'simulink', 'simulink_cosim', 'user_cosim',
       'adams', 'adams_cosim', 'virtual_lab_motion', 'virtual_lab_motion_cosim' ...
    """
    return _AME.AMESetInterfaceTypeForModel(interface_type, circuit)

def AMEGetInterfaceTypeForModel(circuit=None):
    """Returns the name of current interface set in the active circuit.
       If no interface blocks present - returns empty string.
       Typical values : 'simulink', 'simulink_cosim', 'user_cosim',
       'adams', 'adams_cosim', 'virtual_lab_motion', 'virtual_lab_motion_cosim' ...
    """
    return _AME.AMEGetInterfaceTypeForModel(**locals())

def AMEAddBusCreator(alias, inputs, position, snap_ports = True, circuit=None):
    """Adds a component "bus creator"

       Returns alias name of the component added.

       >>> AME.AMEAddBusCreator('new_alias', ['Input 1', 'Input 2'], (10,10), False)
       'new_alias'
    """
    return _AME.AMEAddBusCreator(**locals())

def AMEAddBusSelector(alias, outputs, position, snap_ports = True, circuit=None):
    """Adds a component "bus selector"

       Returns alias name of the component added.

       >>> AME.AMEAddBusSelector('new_alias', ['Input 1', 'Input 2'], (10,10), False)
       'new_alias'
    """
    return _AME.AMEAddBusSelector(**locals())

def AMEAddBusJunction(alias, position, snap_ports = True, circuit=None):
    """Adds a component "bus junction"

       Returns alias name of the component added.

       >>> AME.AMEAddBusJunction('new_alias', (10,10), False)
       'new_alias'
    """
    return _AME.AMEAddBusJunction(**locals())

def AMEAddBusDuplicator(alias, position, snap_ports = True, circuit=None):
    """Obsolete method. Prefer use of AMEAddBusJunction
    """
    return _AME.AMEAddBusJunction(**locals())

def AMEModifyBusCreator(alias_path, inputs):
    """Modifies a component "bus creator"

       Returns alias name of the component added.

       >>> AME.AMEModifyBusCreator('alias_path', ['Input 1', 'Input 2'])
       'new_alias'
    """
    return _AME.AMEModifyBusCreator(**locals())

def AMEModifyBusSelector(alias_path, outputs):
    """Modifies a component "bus selector"

       Returns alias name of the component added.

       >>> AME.AMEModifyBusSelector('alias_path', ['Input 1', 'Input 2'])
       'new_alias'
    """
    return _AME.AMEModifyBusSelector(**locals())

@unsupported_signature("alias_path, password_list = None")
def AMERemoveComponent(alias_path):
    """Removes the component with the given alias path.

       AMERemoveComponent(string)

       String argument is the alias path of the component to remove.

       >>> AMERemoveComponent('th_solid_data_1')
    """
    return _AME.AMERemoveComponent(**locals())

def AMEAddLine(alias, pfrom, pto, circuit=None):
    """Add the line with the given alias path.

       AMEAddLine(string, (int, int), (int, int)[, string])

       String argument is the alias path of the line to add.

       Second argument is the start point of the line

       Third argument is the end point of the line

       Fourth string argument is optional. It is used to identify a different
       circuit from the active circuit in which component is to be added. See also
       SC() and Document().

       >>> AME.AMEAddLine("control", (100,100), (200,200))
    """
    _AME.AMEAddLine(**locals())

@unsupported_signature("alias_path, password_list = None")
def AMERemoveLine(alias_path):
    """Removes the line with the given alias path.

       AMERemoveLine(string)

       String argument is the alias path of the line to remove.

       >>> AME.AMERemoveLine('h2port_6')
    """
    return _AME.AMERemoveLine(**locals())

@unsupported_signature("alias_path, position, password_list = None, snap_ports = True")
def AMEMoveComponent(alias_path, position, snap_ports = True):
    """Moves the component with the given aliaspath to the given position.

       AMEMoveComponent(string, (int, int))

       First string argument is the alias of component to move.

       Second int tuple argument is the (X,Y) position to where the top-left
       corner of the component to be moved, e.g.(50,60).

       Third bool argument is optional. If True, the component will snap and
       autoconnect to close enough ports, otherwise no automatic connection
       will be performed.

       >>> AME.AMEMoveComponent('tp_flow_source_2', (50, 60) )
    """
    return _AME.AMEMoveComponent(**locals())

@unsupported_signature("alias_path, password_list = None, snap_ports = True")
def AMEFlipComponent(alias_path, snap_ports = True ):
    """Flips the component with the given aliaspath.

       AMEFlipComponent(string)

       String argument is the alias path of component to flip.

       Second bool argument is optional. If True, the component will snap and
       autoconnect to close enough ports, otherwise no automatic connection
       will be performed.

       >>> AME.AMEFlipComponent('tp_flow_source_2')
    """
    return _AME.AMEFlipComponent(**locals())

@unsupported_signature("alias_path, password_list = None, snap_ports = True")
def AMERotateComponent(alias_path, snap_ports = True ):
    """Rotates the component with the given alias path.

       AMERotateComponent(string)

       String argument is the alias path of component to rotate.

       Second bool argument is optional. If True, the component will snap and
       autoconnect to close enough ports, otherwise no automatic connection
       will be performed.

       >>> AME.AMERotateComponent('tp_flow_source_2')
    """
    return _AME.AMERotateComponent(**locals())

def AMESelectComponent(alias_path):
    """Selects component with the given alias path.

       AMESelectComponent(string)

       String argument is the alias path of component to select.

       >>> AME.AMESelectComponent('mass2port')
       >>> AME.AMESelectComponent('component_1.mass2port')
    """

    elem_path, circuit_name = _parse_aliaspath(alias_path)
    alias_propid = make_elem_property_id(elem_path, circuit_name)

    # Call
    ret = afp.set(alias_propid + ":cmd=select_component","")
    return ret


def AMEGetSelectedComponents(circuit=None):
    """Return the selected components of the given(or the active) circuit.

       (string, string, ...) = AMESelectComponent(string)

       >>> AME.AMEGetSelectedComponents(AME.Document('model(1)')
       ('mass2port', 'signal04_1')
    """

    circuit_name = _get_circuit(circuit)
    # Call
    ret = afp.get(circuit_name + ":prop=selection")
    elem_list = _StringListFromXML(ret)
    return elem_list

def AMEGetSelectedItems(circuit=None):
    """Return the selected components of the given(or the active) circuit.

       (string, string, ...) = AMESelectComponent(string)

       >>> AME.AMEGetSelectedItems(AME.Document('model(1)')
       ('mass2port', 'signal04_1')
    """
    return _AME.AMEGetSelectedItems(**locals())

def AMEHighlightComponent(alias_path):
    """Highlights the component with the given alias path.

       AMEHighlightComponent(string)

       String argument is the alias path of component to highlight.

       >>> AME.AMEHighlightComponent('mass2port')
       >>> AME.AMEHighlightComponent('component_1.mass2port')
    """

    elem_path, circuit_name = _parse_aliaspath(alias_path)
    alias_propid = make_elem_property_id(elem_path, circuit_name)

    # Call
    ret = afp.set(alias_propid + ":cmd=highlight_component","")
    return ret

def AMECenterComponent(alias_path):
    """Centers the component with the given alias path.

       AMECenterComponent(string)

       String argument is the alias path of component to center.

       >>> AME.AMECenterComponent('mass2port')
       >>> AME.AMECenterComponent('component_1.mass2port')
    """

    # Call
    ret = _AME.AMECenterComponent(**locals())
    return ret

@unsupported_signature("alias_path1, port1, alias_path2,  port2, password_list = None")
def AMEConnectTwoPorts(alias_path1, port1, alias_path2,  port2):
    """Connects the mentioned ports of the mentioned components with a line.

      string = AMEConnectTwoPorts(string, int, string, int)

      First string argument is the alias path of the first component to connect.

      Second int argument is the id of the port of first component.

      Third string argument is the alias path of second component that will connect with the first.

      Fourth int argument is the id of the port of second component.

      Returns the alias name of the line.

      >>> AME.AMEConnectTwoPorts('tp_flow_source_2', 0, 'tp_global_pipe_1', 1)
      'hydraulic'
    """

    elem_path1, circuit_name = _parse_aliaspath(alias_path1)
    elem_path2, circuit_name = _parse_aliaspath(alias_path2)
    alias_propid1 = make_elem_property_id(elem_path1, circuit_name)
    alias_propid2 = make_elem_property_id(elem_path2, circuit_name)
    _ensure_mode( circuit_name, SKETCH_MODE)
    # Call
    ret = afp.get(alias_propid1 +':'+ alias_propid2 + ":connect_2_ports" + '|'+ "port1=" + str(port1) + ',' + "port2=" + str(port2))
    return ret

def enum(**args):
   return type('Enum', (), args)

RESTRICTION = enum(DELETE_COMP='DELETE_COMP', CHANGE_CAT='CHANGE_CAT', CHANGE_ICON='CHANGE_ICON', CHANGE_ALIAS='CHANGE_ALIAS', CHANGE_SUBMODEL='CHANGE_SUBMODEL', CHANGE_PARVAR='CHANGE_PARVAR', CHANGE_CONN_STATUS='CHANGE_CONN_STATUS')

def AMEGetGlobalScriptKey():
   ret = _get_script_global_key()
   return ret

@unsupported_function
def AMESetRestriction(object_reference, enum_restriction,  key, restriction_setter):
   pass

@unsupported_function
def AMERemoveRestriction(object_reference, enum_restriction,  key):
   pass
   
@unsupported_signature("alias_path, comp_port, line_alias_path, line_port, password_list = None")
def AMEConnectComponentToLine(alias_path, comp_port, line_alias_path, line_port):
    """Connects the mentioned ports of the component and line.

      AMEConnectComponentToLine(string, int, string, int)

      First string argument is the alias of the component to connect.

      Second int argument is the id of the port of component.

      Third string argument is the alias of line to connect with component.

      Fourth int argument is the id of the port of the line.

      >>> AME.AMEConnectComponentToLine('tp_flow_source_2', 0, 'pneumatic_4',1)
    """
    return _AME.AMEConnectComponentToLine(**locals())


def AMEGetComponentGeometry(alias):
    """Gives the geometric details(position coordinates, width, height, port positions) of the component.

    ((int, int), (int, int), ((int, int),..)) = AMEGetComponentGeometry(string)

    string argument is the alias of the component for which geometric details have to be fetched.

    Returns
    - position, the component's (x,y) position as a pair of integers.
    - size, the component's (width,height) size in as a pair of integers.
    - ports, a tuple containing (x,y) port positions as pairs of integers.

    >>> AME.AMEGetComponentGeometry('tp_global_pipe_1')
    ((304, 294), (37, 35), ((23, 1), (23, 35)))
   """
    elem_path, circuit_name = _parse_aliaspath(alias)
    alias_propid = make_elem_property_id(elem_path, circuit_name)
    # Call

    if AMEIsLine(alias):
        geometry_list = _StringListFromXML(afp.get(alias_propid + ":get_line_geometry"))
        if (len(geometry_list)>4):
            comp_pos=(int(geometry_list[0]), int(geometry_list[1]))
            comp_width = int(geometry_list[len(geometry_list)-2])-comp_pos[0]
            comp_height = int(geometry_list[len(geometry_list)-1])-comp_pos[1]
            port_pos = (comp_pos, (int(geometry_list[len(geometry_list)-2]),int(geometry_list[len(geometry_list)-1])))

    if AMEIsComponent(alias):
        geometry_list = _StringListFromXML(afp.get(alias_propid + ":get_component_geometry"))
        if (len(geometry_list)>4):
            comp_pos=(int(geometry_list[0]), int(geometry_list[1]))
            comp_width = int(geometry_list[2])
            comp_height = int(geometry_list[3])
            port_cnt = int(geometry_list[4])

            port_pos=()

            for i in range(6, len(geometry_list), 2):
                current_port = (int(geometry_list[i-1]), int(geometry_list[i]))
                port_pos = port_pos +(current_port,)

    return (comp_pos,(comp_width, comp_height), port_pos)

def AMEGetComponentIcon(alias_path, accept_reverse=False):
    """Return the SVG code for the icon of a component
       like it appears on the circuit.

       (string) = AMEGetComponentIcon(string, bool)

       String argument is the component alias path.

       Second argument is optional. If True and if the icon on the circuit
       has its colors inverted, then the colors of the return SVG code will be inverted.

       The return icon code takes into account the framework and layer of the component,
       but not the rotation and the flip of the icon. See AMEGetComponentIconTransformation().

       >>> AMEGetComponentIcon('constant')
    """

    # Call
    return _AME.AMEGetComponentIcon(**locals())

def AMEGetComponentIconTransformation(alias_path):
    """Provides the transformation information (number of rotations and flip) for the icon of a component.

       (int, bool) = AMEGetComponentIconTransformation(string)

       String argument is the component alias path.

       It returns a tuple:
       - the first element is the number of rotations of the icon (in range [0, 3]),
       - the second element indicates if the icon has been flipped: True if flipped, False otherwise.

       Note that the transformation of the icon is determined first by the number of rotations
       and then by the flip.

       >>> AMEGetComponentIconTransformation('constant')
       (1, True)
    """

    # Call
    comp_transformation = _StringListFromXML(_AME.AMEGetComponentIconTransformation(**locals()))
    nb_rotations = int(comp_transformation[0])
    is_flipped = comp_transformation[1]=='True'

    return (nb_rotations, is_flipped)

def AMEGetLineGeometry(alias):
    """Gives the geometric details (line points) of the line.

    (int, int),...) = AMEGetLineGeometry(string)

    string argument is the alias of the line for which geometric details have to be fetched.

    Returns a tuple containing the position of line points as (x,y)
    pairs of integers.

    >>> AME.AMEGetLineGeometry('pneumatic_4')
    ((326, 294), (326, 546), (518, 546))

    """
    elem_path, circuit_name = _parse_aliaspath(alias)
    alias_propid = make_elem_property_id(elem_path, circuit_name)
    # Call
    geometry_list = _StringListFromXML((afp.get(alias_propid + ":get_line_geometry")))

    point_pos=()
    for i in range(1, len(geometry_list), 2):
        point_pos = point_pos + ((int(geometry_list[i-1]), int(geometry_list[i])),)

    return point_pos

def AMEGetLibraryIconGeometry(icon_name):
    """Gives the geometric details (width, height, port positions) of the component.

    ((int, int), ((int, int),..)) = AMEGetLibraryIconGeometry(string)

    string argument is the id of component icon for which geometric details have to be fetched.

    Returns
    - size, the component's size as a (width,height) pair of integers
    - ports, a tuple containing (x,y) port positions as pairs of integers

    >>> AME.AMEGetLibraryIconGeometry('meca.mass2port')
    ((49, 31), ((49, 16), (1, 16)))

   """
    geometry_list = _StringListFromXML((afp.get(icon_name + ":get_icon_geometry")))

    comp_width=''
    comp_height=''
    if(len(geometry_list)>1):
        comp_width = int(geometry_list[0])
        comp_height = int(geometry_list[1])

    port_pos=()

    for i in range(3, len(geometry_list), 2):
        port_pos = port_pos + ((int(geometry_list[i-1]), int(geometry_list[i])),)

    return((comp_width, comp_height), port_pos)

def AMEGetParameterValue(data_path):
    """Finds a parameter (or state variable) in the current active circuit, then gives its value (or initial value).

       (string, string ) = AMEGetParameterValue(string)
       (string, string ) = AMEGetParameterValue(AMEParVar)

       The argument is either a string corresponding to the path of the
       parameter given under the form:
           parameter_name@comp_alias_0.comp_alias_i.comp_alias_N,
       or an AMEParVar object corresponding to the parameter, as returned by AMEGetParVar
       or an AMEParVarIteration.

       Returns a tuple containing two strings.
       First returned string is the parameter value.
       Second returned string is unit in which the value is expressed. This is None for text or integer parameter.

       >>> AME.AMEGetParameterValue('force0@springdamper01')
       ('1.96200000000000e+003', 'N')

    """
    data_propid = make_data_property_id(*_parse_datapath(data_path))
    value = afp.get(data_propid + ':data_value')
    try:
        unit = afp.get(data_propid + ':data_unit')
    except:
        unit = None
    return (value, unit)

@unsupported_signature("data_path, value, password_list = None")
def AMESetParameterValue(data_path, value):
    """Sets the value of a parameter or the initial value of a state.

       AMESetParameterValue(string, string)
       AMESetParameterValue(AMEParVar, string)

       First argument is either a string corresponding to the path of the
       parameter given under the form:
           parameter_name@comp_alias_0.comp_alias_i.comp_alias_N,
       or an AMEParVar object corresponding to the parameter, as returned by AMEGetParVar
       or an AMEParVarIteration.

       Second string argument is the value to be set to the parameter.

       >>> AME.AMESetParameterValue('theta@mass1port', '90')
    """
    var_name, elem_path, circuit_name = _parse_datapath(data_path)
    datapath = _make_datapath(var_name, elem_path, circuit_name)
    return _AME.AMESetParameterValue(datapath, value)

@unsupported_signature("data_path, password_list = None")
def AMESetParameterDefaultValue(data_path):
    """Sets the default value of a parameter.

       AMESetParameterDefaultValue(string)
       AMESetParameterDefaultValue(AMEParVar)

       First argument is either a string corresponding to the path of the
       parameter given under the form:
           parameter_name@comp_alias_0.comp_alias_i.comp_alias_N,
       or an AMEParVar object corresponding to the parameter, as returned by AMEGetParVar
       or an AMEParVarIteration.

       >>> AME.AMESetParameterDefaultValue('theta@mass1port')
    """
    var_name, elem_path, circuit_name = _parse_datapath(data_path)
    datapath = _make_datapath(var_name, elem_path, circuit_name)
    return _AME.AMESetParameterDefaultValue(datapath)

@unsupported_signature("data_path, password_list = None")
def AMEGetParameterInfos(data_path):
    """Provides basic information about a parameter which belongs the current active circuit.

       (string, string, string) = AMEGetParameterInfos(string)

       The argument is either a string corresponding to the path of the data
       under the form: data_name@comp_alias_0.comp_alias_i.comp_alias_N,
       or an AMEParVar object.

       It returns a tuple containing three strings.
       First returned string is the parameter type. It can be 'ame_real_parameter', 'ame_integer_parameter', 'ame_text_parameter' or 'ame_parameter_undefined'.
       Second returned string is the parameter title.
       Third returned string is the parameter unit.

       >>> AME.AMEGetParameterInfos('rp9@h2port')
       ('ame_real_parameter', 'diameter of pipe', 'mm')

    """
    data_propid = make_data_property_id(*_parse_datapath(data_path))
    type = afp.get(data_propid + ":data_type")
    title = afp.get(data_propid + ":data_title")
    try:
        unit = afp.get(data_propid + ":data_unit")
    except:
        unit = None
    return (type, title, unit)

def AMEGetGlobalParameterValue(data_path):
    """Finds then gives the value of global parameter in the current active circuit.

       (string, string) = AMEGetGlobalParameterValue(string)

       The string argument is the unique name of the global parameter.

       It returns a tuple containing the global parameter value and
       the unit in which the value is expressed. For a text or an integer global parameter, this is None.

       >>> AME.AMEGetGlobalParameterValue('p_diameter')
       ('92.2', 'mm')

    """
    varname, elempath, circuit = _parse_datapath(data_path)
    data_propid = make_data_property_id(varname, elempath, circuit)
    if elempath:
        raise DataPathError("Expected path to global parameter, got data from '%s' element" % elempath)
    value = afp.get(data_propid + ':data_value')
    try:
        unit = afp.get(data_propid + ':data_unit')
    except:
        unit = None
    return (value, unit)

@unsupported_signature("data_path, value, password_list = None")
def AMESetGlobalParameterValue(data_path, value):
    """Finds then sets the value of global parameter in the current active circuit.
       Note the sketch is changed to parameter mode.

       AMESetGlobalParameterValue(string, string)

       First string argument is unique name of the global parameter.

       Second string argument is value to set to the global parameter.

       >>> AME.AMESetGlobalParameterValue('p_diameter', 92.2)
    """
    return AMESetParameterValue(data_path, value)

def AMEGetActiveCircuit():
    """Gives the name of the active working circuit.

       string = AMEGetActiveCircuit()

       Returns the name of the current active circuit
       with its unique identifier.

       >>> AME.AMEGetActiveCircuit()
       'my_new_system(1)'
    """
    return _get_current_circuit()

def AMESetActiveCircuit(circuit_name):
    """Sets a circuit to be the active working circuit.
       Note the circuit must be opened.

       AMESetActiveCircuit(string)

       The string argument is the name of the circuit to set active.
       Note the circuit name should be given with unique identifier.

       >>> AME.AMESetActiveCircuit('my_new_system(1)')
    """
    threading.currentThread()._current_circuit = circuit_name

def AMEGetOpenedCircuitList():
    """Gives the list of opened circuit names.

       (string, ...) = AMEGetOpenedCircuitsList()

       The returned tuple is the list of opened circuits.

       >>> AME.AMEGetOpenedCircuitList()
       ('my_system(1)', 'testFriction(1)')
    """
    tree = ET.XML(afp.get("prop=open_circuits"))
    return tuple([element.text for element in tree.findall('circuit/circuit-name')])

def AMEGetOpenedCircuitsDirectoriesPathsList():
    r"""Gives the list of opened circuit directories paths.

       (string, ...) = AMEGetOpenedCircuitsDirectoriesPathsList()

       The returned tuple is the list of opened circuits directories paths.

       >>> AME.AMEGetOpenedCircuitsDirectoriesPathsList()
       ('C:\my_system_directory', 'C:\testFriction_directory')
    """
    tree = ET.XML(afp.get("prop=open_circuits_dir_paths"))
    return tuple([element.text for element in tree.findall('circuit/circuit-name')])

###############################################################################
# \brief
# \version 2019-08-08 GCi CORE-16179:
#     Set the submodel_path optional according to the documentation
###############################################################################
@unsupported_signature("alias_path, submodel_name, submodel_path = None , force_change = False, copy_common_parameters = False, password_list = None")
def AMEChangeSubmodel(alias_path, submodel_name, submodel_path = None , force_change = False, copy_common_parameters = False):
    """Sets a submodel to the component or the line in the current active circuit.

       AMEChangeSubmodel(string, string, string[, bool, bool])
       AMEChangeSubmodel(AMECompLine, string, string[, bool, bool])

       First argument is a string representing the alias path of the element (component or line)
       whose submodel will be set, or an AMECompLine object, as returned by AMEGetCompLine or an
       AMECompLineIteration.

       Second string argument is the name of the submodel to set.

       Third string argument is directory where the submodel resides.  If it is not
       set, submodel directory is fetched from paths list.

       Fourth argument if set to False (or 0) will force submodel to change.

       Fifth argument if set to True (or 1) will copy common paramters of current
       submodel to the submodel to set.

       >>> AME.AMEChangeSubmodel('signal03', 'UD00', '$AME/submodels')
    """
    return _AME.AMEChangeSubmodel(**locals())

def AMEGetSubmodelInfos(alias_path):
    """Returns the submodel name and path for a given element.

       (string, string) = AMEGetSubmodelInfos(string)
       (string, string) = AMEGetSubmodelInfos(AMECompLine)

       First argument is a string representing the alias path of the element (component or line)
       whose submodel will be set, or an AMECompLine object, as returned by AMEGetCompLine or an
       AMECompLineIteration.

       >>> AME.AMEGetSubmodelInfos('myicon')
       ('MY_SUBMODEL', 'D:/my_library/submodels')
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))

    tree = ET.XML(afp.get(alias_propid + ':comp_subname_and_path_info'))
    submodel_name = tree.findtext("submodel-name")
    if not submodel_name or submodel_name == ' ':
        submodel_name = None
    submodel_path = tree.findtext("submodel-path")
    if not submodel_path or submodel_path == ' ':
        submodel_path = None

    return submodel_name, submodel_path

def AMEHasSensedVariables(alias_path):
    """Tells if the submodel of the given element has sensed internal variables.

        bool = AMEHasSensedVariables(string)

        First argument is a string representing the alias path of the element (component or line)
        to test.

        >>> AME.AMEHasSensedVariables('myicon')
        False (or True)
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return bool(int(afp.get(alias_propid + ':comp_submodel_has_sensed_variables')))

def AMEGetSensedSubmodelInfos(alias_path):
    r"""Returns the sensed submodel name and path and the source submodel name
       and path for a given element with sensed internal variables.

        (string, string, string, string) = AMEGetSensedSubmodelInfos(string)

        First argument is a string representing the alias path of the element (component or line)
        from which submodels information have to be retrieved.

        Outputs:
            - string: the name of the submodel with sensed internal variables
                      Remark: If the submodel of the given element is not a
                              submodel with sensed variables, this name will be 'None'
            - string: the path to the submodel with sensed internal variables
                      Remarks:
                              1. In the current version, this path will always
                                 be 'None' because sensed submodels cannot be saved
                                 in libraries and so are always local to AMESim models
                              2. If the submodel of the given element is not a
                                 submodel with sensed variables, this name will be 'None'
            - string: the name of the source submodel in which internal variables
                      have been sensed
                      Remark: If the submodel of the given element is not a
                              submodel with sensed variables, this name will
                              be the name of the submodel of the given element
            - string: the path of the source submodel in which internal variables
                      have been sensed
                      Remark: If the submodel of the given element is not a
                              submodel with sensed variables, this path will be
                              the path of the submodel of the given element


        >>> AME.AMEGetSensedSubmodelInfos('myicon')
        ('MY_SUBMODEL_SENSED', 'C:\sensed_library_dir\submodels', 'MY_SUBMODEL', 'C:\library_dir\submodels')
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))

    tree = ET.XML(afp.get(alias_propid + ':comp_sensed_submodel_info'))
    sensed_submodel_name = tree.findtext("sensed-submodel-name")
    if not sensed_submodel_name or sensed_submodel_name == ' ':
        sensed_submodel_name = None
    sensed_submodel_path = tree.findtext("sensed-submodel-path")
    if not sensed_submodel_path or sensed_submodel_path == ' ':
        sensed_submodel_path = None
    src_submodel_name = tree.findtext("source-submodel-name")
    if not src_submodel_name or src_submodel_name == ' ':
        src_submodel_name = None
    src_submodel_path = tree.findtext("source-submodel-path")
    if not src_submodel_path or src_submodel_path == ' ':
        src_submodel_path = None

    return sensed_submodel_name, sensed_submodel_path, src_submodel_name, src_submodel_path


def AMEGetMode(circuit=None):
    """Returns the name of the mode of the given circuit (or the
       active circuit) as a string.

       (string) = AMEGetMode()
       (string) = AMEGetMode(string)

       The argument is the circuit name. It is optional. If None, then the current active circuit name is used.

       It returns the actual active mode name for the given circuit. The 4 possible modes are:
       - 'sketch_mode'
       - 'submodel_mode'
       - 'parameter_mode'
       - 'simulation_mode'

    Example:
    >>> AMEGetMode()
    'sketch_mode'
    """
    if circuit is None:
        circuit = _get_current_circuit()
    return _get_mode_name(_get_mode(circuit))

def AMEGetAPIVersion():
    """Provides API version information.

       (string) = AMEGetAPIVersion()

       First int is major version number. It changes for major release.
       Second int is update version number. It changes for a update release.
       Third int is hofix version number. It changes for hofix release.
       The string is the complete release version string.

       >>> AME.AMEGetAPIVersion()
       ('20222..')
       ('20222.1.1')
    """
    tree = ET.XML(afp.get('prop=ame_version'))
    major = tree.findtext("major-version")
    update = tree.findtext("update-version")
    hotfix = tree.findtext("hotfix-version")
    version_string = tree.findtext("version-string")
    return (version_string)

# version 2013-04-02 SPm 0109212: Added default value to dataset parameter.
def AMEGetVariableFinalValue(data_path, dataset=None):
    """Reads the last variable value from the specifed results file in the current active circuit.

       (double, double) = AMEGetVariableFinalValue(string[, string])

       First argument is either a string corresponding to the path of the variable, or an
       AMEParVar object, as returned by AMEGetParVar or an AMEParVarIteration.

       Second string argument is the extension of the results file to read.
       By default it reads the 'circuit_name_.results' file, where 'circuit_name' is the name of
       the active circuit.
       Set it to '2' if you wish to read 'circuit_name_.results.2' results file.

       It returns tuple containing the last time value and the last variable value.

       >>> AME.AMEGetVariableFinalValue('press@fluidprops', '2')
       (1000.0000000000001, 898.34208625924987)
    """
    varname, elempath, circuit = _parse_datapath(data_path)
    data_propid = make_data_property_id(varname, elempath, circuit)
    if _get_mode(circuit) < _get_mode_index(PARAMETER_MODE):
        _change_mode(circuit, PARAMETER_MODE)
    if not dataset:
        dataset = "ref"

    tree = ET.XML(afp.get(data_propid + ':variable_last_result_with_sampling|dataset=%s' % urllib.parse.quote(dataset)))
    last_value = float(tree.findtext("last-value"))
    last_sampling_value = float(tree.findtext("last-sampling-value"))

    return (last_sampling_value, last_value)

# version 2013-04-02 SPm 0109212: Added default value to dataset parameter.
# version 2014-08-08 AMp 153544: for getting values mode should be atleast parameter mode.
def AMEGetVariableValues(data_path, dataset=None):
    """Reads the variable values from the specifed result file of the current active circuit.

       ((double, double), ...) = AMEGetVariableValues(string[, string])

       First argument is either a string corresponding to the path of the variable, or an
       AMEParVar object, as returned by AMEGetParVar or an AMEParVarIteration.

       Second string argument is the extesnion of the results file to read.
       By default it reads the 'circuit_name_.results' file, where 'circuit_name' is the name of
       the active circuit.
       Set it to '2' if you wish to read 'circuit_name_.results.2' results file.

       It returns tuple containing pairs of times and values.

       >>> AME.AMEGetVariableValues('press@fluidprops')
       ((0.0, 9.2350599537811156e-005), (100.00000000000023, 9.0267566515905919), (200.00000000000045, 37.182831099831255),
        (300.00000000000068, 84.014292131376521), (400.00000000000091, 149.32977089654025), (500.00000000000114, 232.67311255595379),
       (600.00000000000136, 333.48061740306184), (700.00000000000159, 451.12132055729285), (800.00000000000182, 584.95112810520152),
       (900.00000000000205, 734.28997366879526), (1000.0, 898.42224851630579))
    """
    varname, elempath, circuit = _parse_datapath(data_path)
    data_propid = make_data_property_id(varname, elempath, circuit)
    if _get_mode(circuit) < _get_mode_index(PARAMETER_MODE):
        _change_mode(circuit, PARAMETER_MODE)
    if not dataset:
        dataset = "ref"

    tree = ET.XML(afp.get(data_propid + (':cmd=create_variable_results_buffer|dataset=%s' % urllib.parse.quote(dataset))))
    id = tree.findall("id")[0].text
    vlen = int(tree.findall("values/length")[0].text)
    slen = int(tree.findall("sampling-values/length")[0].text)

    # Decode pointers from the base64 text
    if sys.version_info[0] <3:
        vptr = struct.unpack('P', tree.findall("values/addr")[0].text.decode('base64'))[0]
        sptr = struct.unpack('P', tree.findall("sampling-values/addr")[0].text.decode('base64'))[0]
    else:
        import base64
        vptr = struct.unpack('P', base64.b64decode(tree.findall("values/addr")[0].text))[0]
        sptr = struct.unpack('P', base64.b64decode(tree.findall("sampling-values/addr")[0].text))[0]


    # Dereference pointers as pointing to double arrays
    from ctypes import cast, POINTER, c_double
    values = cast(vptr, POINTER(c_double*vlen)).contents[:]
    sampling_values = cast(sptr, POINTER(c_double*slen)).contents[:]

    afp.set("cmd=destroy_variable_results_buffer|id=%s" % id, "")

    return list(zip(sampling_values, values))

def AMEClearUndoStack(circuit = None):
    """Clears the undo/redo stack for the working circuit, preventing the user
       from undoing the last set of actions.

       If this function is called as part of a macro-command, then the undo/redo
       stack will only be cleared after the macro-command is complete.

       >>> AME.AMEClearUndoStack()

    """
    document = _get_document(circuit)
    circuit_propid = make_circuit_property_id(document, CIR_CLEAR_UNDO_STACK)
    afp.set(circuit_propid, "")

def AMEBeginMacroCommand(macro_name, circuit = None):
    """Begins a macro command with the given name.  All actions performed on the
       working circuit between a call to this function and the corresponding
       call to AMEEndMacroCommand will be grouped in one undo/redo command, and
       will appear in the GUI as one undoable action of the working circuit.

       Macro commands can be nested: It is possible to call
       AMEBeginMacroCommand and AMEEndMacroCommand between two other calls to
       these same functions. They must be properly nested, and not cross each
       other.

       Warning: failing to match a call to AMEBeginMacroCommand with an
       appropriate call to AMEEndMacroCommand may leave the application in
       invalid state. To avoid that, please consider using "try...finally"
       statement to ensure AMEEndMacroCommand is called:

          AMEBeginMacroCommand("Perform multiple actions")
          try:
             ... # perform actions
          finally:
             AMEEndMacroCommand("Perform multiple actions")

       >>> AME.AMEBeginMacroCommand("Large command")
       >>> AME.AMESetParameterValue("param1@component", "value1")
       >>> AME.AMESetParameterValue("param2@component", "value2")
       >>> AME.AMEEndMacroCommand("Large command")

       Advantage of AMEBeginMacroCommand and AMEEndMacroCommand:
       It will help to improve performance of lengthy operations. It is common that
       parameter values of the component is modified several times. Each
       modification will try to find the new sync status of the associated
       supercomponent. This will overload Amesim.

       Hence it is suggested to use AMEBeginMacroCommand and AMEEndMacroCommand
       for lengthy operations.

       AMEBeginMacroCommand:  This will stop the sync status verification.
       AMEEndMacroCommand  :  This will resume sync status verification.

        Example:
          def my_function(self):
             AME.AMEBeginMacroCommand("lengthy_action_name")
             try:
                AME.AMESetParameterValue("param_1@component", "value1")
                AME.AMESetParameterValue("param_2@component", "value2")
                .....
                .....
                AME.AMESetParameterValue("param_n@component", "value_n")
                AME.AMEGetParameterValue('par_name@component')
             finally:
                AME.AMEEndMacroCommand("lengthy_action_name")

       Warning:
       Failing to match a call to AMEBeginMacroCommand with an appropriate
       call to AMEEndMacroCommand may stop the automatic update of sync status.
    """
    document = _get_document(circuit)
    circuit_propid = make_circuit_property_id(document, CIR_BEGIN_CMD)
    afp.set(circuit_propid, macro_name)


def AMEEndMacroCommand(macro_name, circuit = None):
    """Ends a macro command with the given name, which must have been started by
       calling AMEBeginMacroCommand with the same name.  All actions performed
       on the working circuit since the call AMEBeginMacroCommand will be
       grouped in one undo/redo command, and will appear in the GUI as one
       undoable action.

       Macro commands can be nested: It is possible to call
       AMEBeginMacroCommand and AMEEndMacroCommand between two other calls to
       these same functions. They must be properly nested, and not cross each
       other.

       >>> AME.AMEBeginMacroCommand("Large command")
       >>> AME.AMESetParameterValue("param1@component", "value1")
       >>> AME.AMESetParameterValue("param2@component", "value2")
       >>> AME.AMEEndMacroCommand("Large command")
    """
    document = _get_circuit(circuit)
    circuit_propid = make_circuit_property_id(document, CIR_END_CMD)
    afp.set(circuit_propid, macro_name)

def AMERegisterCustomCommand(display_name, callback, circuit = None):
    """Registers a custom undo/redo command that will appear with the given
       display name. The given callback will be called with the display name and
       the undo_direction argument set to either UNDO or REDO when the command
       is undone or redone. A "redo" will be immediately performed as the
       command is the registered.

       This custom command can be included in macro commands.

       A callback should have the following signature:

       def callback(display_name, undo_direction):
          return None

       >>> class State:
       ...    pass
       >>> state = State()
       >>> state.undo_count = 0
       >>> state.redo_count = 0
       >>> def ChangeCallback(display_name, undo_direction):
       ...   if undo_direction == UNDO:
       ...     state.undo_count += 1
       ...   else:
       ...     state.redo_count += 1
       >>> AMERegisterCustomCommand("Changing 'a'", ChangeCallback)
       >>> state.undo_count
       0
       >>> state.redo_count
       1
       >>> # Users undoes from GUI
       >>> state.undo_count
       1
       >>> state.redo_count
       1
       >>>
    """
    document = _get_document(circuit)
    circuit_propid = make_circuit_property_id(document, CIR_CUSTOM_UNDO)
    callback_key = _RegisterCustomCommandCallback(document, callback)
    value = _StringListToXML([display_name, callback_key])
    afp.set(circuit_propid, value)

# # CAD2AME SUPERCOMPONENT API functions
# ########Starting########################################

# def AMEOpenSupercomponent(comp_alias):
#     """
#     Opens a supercomponent instance corresponding to the given
#     supercomponent's alias.
#     """
#     elem_path, circuit = _parse_aliaspath(comp_alias)
#     alias_propid = make_elem_property_id(elem_path, circuit)
#     _ensure_mode( circuit, SKETCH_MODE)
#     ret_value = afp.set(alias_propid + ':cmd=open_supercomponent', "")
#     return (ret_value)

# def AMECreateEmptySupercomponent(icon_name, alias, position, submodel_name, circuit = None):
#     """
#     Creates a new port-less, empty, local supercomponent at a given (x,y)
#     location in the given circuit, with a given icon name and submodel name.

#     string = AMECreateEmptySupercomponent(string, string, (integer, integer), string)
#     string = AMECreateEmptySupercomponent(string, string, (integer, integer), string, string)

#     - First string argument is the icon name of the new empty supercomponent.

#     - Second string argument is the alias of the component to create. If a
#       non-empty alias is given, the function will fail if another component or
#       line with the same alias already exists in the circuit. If empty, an alias
#       will be automatically generated.

#     - Third argument is a position where the new empty supercomponent has to be created.

#     - Fourth string argument is the submodel name of the new empty
#       supercomponent. If empty, a new submodel name will be created.

#     - Fifth string argument is optional. It is used to identify a different
#        circuit from the active circuit in which component is to be added. See also
#        SC() and Document().

#     It returns the alias of the newly created empty supercomponent.

#     >>> AME.AMECreateEmptySupercomponent("icon_name", "", (100, 100), "SUBMODEL_NAME")
#     "icon_name"
#     """
#     circuit = _get_circuit(circuit)
#     _ensure_mode( circuit, SKETCH_MODE)
#     ret_value = afp.get(
#           "%s:cmd=create_empty_supercomponent|x=%s,y=%s,icon_name=%s,submodel_name=%s,alias=%s"
#           % (circuit, str(position[0]), str(position[1]), icon_name, submodel_name, alias))
#     return (ret_value)

# def AMEAddSupercomponentPort( port_type,position, port_face, circuit = None):
#     """
#     Adds a port of a given type and on a given face to an existing supercomponent,
#     and put the port label at the given location (x,y) on the current sketch.

#      string = AMEAddSupercomponentPort(string,(integer,integer),string)
#      string = AMEAddSupercomponentPort(string,(integer,integer),string, string)

#     -First string argument is the port type of the new port to be added.

#     -Second argument is a position where the new port has to be added.

#     -Third string argument is the port face of the new port to be added.
#      Accepted values are "face_top", "face_bottom", "face_left", "face_right",
#      "face_topleft", "face_topright", "face_bottomleft" and "face_bottomright"

#     -Fourth string argument is optional. It is used to identify a different
#      circuit from the active circuit in which component is to be added. See also
#      SC() and Document().

#     It returns the port id of the newly added port.

#      >>> AME.AMEAddSupercomponentPort("pflow", (150,150), "face_top", AME.SC("component_1"))
#      'id_0'
#     """
#     return _AME.AMEAddSupercomponentPort(**locals())

# def AMEDisassembleSupercomponent(alias_name, scp_action = "no_action"):
#     """
#     Dissolve a supercomponent given its alias

#      list[] = AMEDissolveSupercomponent(string, "create_params")

#     -First string argument is alias of the supercomponent we want to dissolve

#     -Second argument is the action to perform for global parameters.

#     It returns the list of all alias of the new extracted components

#      >>> AME.AMEDissolveSupercomponent("my_supercomponent_alias", "")
#      ['my_comp_alias1', 'my_comp_alias2', 'my_comp_alias3']
#     """
#     return _AME.AMEDisassembleSupercomponent(**locals())

# @unsupported_signature("port_id, circuit = None, password_list = None")
# def AMERemoveSupercomponentPort(port_id, circuit = None):
#     """
#     Removes a port corresponding to the given port id from the given circuit.

#     AMERemoveSupercomponentPort(string)
#     AMERemoveSupercomponentPort(string, string)

#     First string argument is the port id of the port to be deleted from the supercomponent.

#     Second string argument is optional. It is used to identify a different
#     circuit from the active circuit in which component is to be added. See also
#     SC() and Document().

#     >>> AME.AMERemoveSupercomponentPort("id_1", AME.SC("component_1"))
#     """
#     return _AME.AMERemoveSupercomponentPort(**locals())

# def AMEGetSupercomponentPortIds(circuit = None):
#     """
#     Returns the list of port ids in the given supercomponent.

#     list[] = AMEGetSupercomponentPortIds()
#     list[] = AMEGetSupercomponentPortIds(string)

#     string argument is optional. It is used to identify a different
#        circuit from the active circuit in which component is to be added. See also
#        SC() and Document().

#     Returns the list of port ids of the active circuit or given circuit respectively.

#     >>>port_id_list = AME.AMEGetSupercomponentPortIds(AME.SC("component_1"))
#     """
#     circuit = _get_circuit(circuit)
#     ret_value = afp.get(circuit+":get_supercomponent_port_ids|")
#     if ret_value:
#         return ret_value.split(":")
#     return []

# def AMESetPortName(port_id, name, circuit = None):
#     """
#     Sets the port label corresponding to the port id with the given name, in the given circuit.

#     AMESetPortName(string, string)
#     AMESetPortName(string, string , string)

#     -First string argument is the port id of port of which the label has to be updated.

#     -Second string argument is the new port label to be set.

#     -Third string argument is optional. It is used to identify a different
#        circuit from the active circuit in which component is to be added. See also
#        SC() and Document().

#     >>>AME.AMESetPortName("id_1", "port_1", AME.SC("component_1"))
#     """
#     return _AME.AMESetPortName(**locals())

# def AMEGetPortTag(alias, port_number):
#     """
#     Gets the port tag corresponding to the port id in the given circuit.

#     AMEGetPortTag(string, string)

#     First string argument is the alias of the component to which the port belongs.

#     Second string argument is the port number of the port for which the tag will be fetched.

#     >>> AME.AMEGetPortTag("dynamic_transmitter", 2)
#     """
#     elem_path, circuit_name = _parse_aliaspath(alias)
#     alias_propid = make_elem_property_id(elem_path, circuit_name)
#     ret_value = afp.get(alias_propid + ":get_port_tag|" + "port_number=" + urllib.parse.quote(str(port_number)))
#     return (ret_value)

# def AMESetPortTag(alias_path, port_number, port_tag):
#     """
#     Sets the port tag corresponding to the port id with the given value, in the given circuit.

#     AMESetPortTag(string, string, string)

#     First string argument is the alias of the component which its port tag has to be updated.

#     Second string argument is the port number of the port for which the tag will be updated.

#     Third string argument is the new value of the port tag which has to be updated.

#     >>> AME.AMESetPortTag("dynamic_transmitter", 2, "value")
#     """
#     return _AME.AMESetPortTag(**locals())


# @unsupported_signature("circuit = None, password_list = None")
# def AMEMakeSupercomponentLocal(circuit = None):
#     """
#     Flags a supercomponent as local of the given circuit.

#     AMEMakeSupercomponentLocal()
#     AMEMakeSupercomponentLocal(string)

#     Pass the supercomponent circuit which has to be flagged as local.

#     >>>AME.AMEMakeSupercomponentLocal(AME.SC("component_1"))
#     """
#     circuit = _get_circuit(circuit)
#     _ensure_mode( circuit, SKETCH_MODE)
#     ret_value = afp.set(circuit+":make_supercomponent_local", "")
#     return (ret_value)

# @unsupported_signature("image, circuit = None, password_list = None")
# def AMESetSupercomponentImage(image, circuit = None):
#     """
#     Sets the image of a supercomponent, given an image as a base64-encoded XPM file contents.

#     AMESetSupercomponentImage(image[, string])

#     First argument is the base64-encoded XPM file contents.

#     Second string argument is optional. It is used to identify a different
#     circuit from the active circuit in which component is to be added. See also
#     SC() and Document().

#     >>AME.AMESetSupercomponentImage(image, AME.SC("component_1"))
#     """
#     return _AME.AMESetSupercomponentImage(**locals())

# def AMESetSupercomponentIcon(icon_path, circuit):
#     """
#     Change the icon of the supercomponent. Icon file should contain the
#     necessary port information

#     AMESetSupercomponentIcon(string, circuit)

#     First argument is the path of the icon file. It can be either .svg or .xbm
#     Second argument is the supercomponent circuit for changing the icon

#     >>>AME.AMESetSupercomponentIcon(icon_path, AME.SC("component_1"))
#     """
#     circuit = _get_circuit(circuit)
#     _ensure_mode(circuit, SKETCH_MODE)
#     ret_value = afp.set(circuit+":cmd=set_supercomponent_icon" , icon_path)
#     return (ret_value)

# def AMESetElementColor(alias_path, color):
#     """
#     Change the icon color of a component/line.

#     AMESetElementColor(alias_path, string)

#     First argument is the component/line alias path
#     Second argument is the color string

#     >>> AME.AMESetElementColor("constant", "#cc3333")
#     >>> AME.AMESetElementColor("component_1", "#FF0000")
#     >>> AME.AMESetElementColor("component_1.sim_params", "#FFFF00")
#     """

#     return _AME.AMESetElementColor(**locals())

# def AMEGetElementColor(alias_path):
#     """
#     Get the icon color of component/line

#     AMEGetElementColor(alias_path)

#     First argument is the component/line alias path

#     >>> AME.AMEGetElementColor("constant")
#     """

#     return _AME.AMEGetElementColor(**locals())

# def AMEAttachAppToSupercomponent(app_path, parameter_mode, simulation_mode, circuit, app_name = ""):
#     """
#     Attach the given app to the supercomponent.

#     AMEAttachAppToSupercomponent(string, bool, bool, circuit, string)

#     First argument is the path of the app.

#     Second argument is boolean for launching tool on mouse double click in parameter mode.
#     Third argument is boolean for launching tool on mouse double click in simulation mode.

#     Fourth argument is the supercomponent circuit for attaching the app

#     Fifth argument is optional. If given, it will set the same name to the app.

#     >>>AME.AMEAttachAppToSupercomponent("C://apps/testapp.app", True, False, AME.SC("component_1"), "my_app")
#     """

#     return _AME.AMEAttachAppToSupercomponent(**locals())

# def AMEAttachPlotConfigurationToSupercomponent(plot_configuration_path, circuit, my_plot_name = ""):
#     """ 
#     Attach the given plot configuration file (*.plt) to the supercomponent.

#     AMEAttachPlotConfigurationToSupercomponent(string, circuit, string)

#     First argument is the path of the plot configuration file (*.plt).

#     Second argument is the supercomponent circuit for attaching the plot configuration file (*.plt).

#     Third argument is optional. If given, it will set the name of the plot configuration to be displayed in the user interface.

#     >>>AME.AMEAttachPlotConfigurationToSupercomponent("C://apps/testPlotConfig.plt", AME.SC("component_1"), "my_plot_name")
#     """

#     return _AME.AMEAttachPlotConfigurationToSupercomponent(**locals())


# def AMECloseSupercomponentWindow(circuit, close_children = False):
#     """
#     Closes the sketch window of the given supercomponent circuit.

#     AMECloseSupercomponentWindow(circuit, bool)

#     First argument is the supercomponent circuit which has to be closed.

#     Second argument is boolean for closing its children sketches.

#     >>>AME.AMECloseSupercomponentWindow(AME.SC("component_1"), False)
#     """
#     ret_value = afp.set(circuit+":cmd=close_supercomponent_window" , str(bool(close_children)))
#     return (ret_value)

# @unsupported_signature("comp_aliaspath, comp_port_number, sc_port_id, circuit = None, password_list = None")
# def AMEConnectSupercomponentPort(comp_aliaspath, comp_port_number, sc_port_id, circuit = None):
#     """
#     Connects a supercomponent port in the given circuit, as identified by its port id, to a port of a component.

#     AMEConnectSupercomponentPort(string, int, string[, string])

#     First argument is the alias path of the component.

#     Second argument is the port number of the component to be connected to.

#     Third argument is the port id of the port to be connected.

#     Fourth string argument is optional. It is used to identify a different
#     circuit from the active circuit in which component is to be added. See also
#     SC() and Document().

#     >>>AME.AMEConnectSupercomponentPort("1111(1).constant", 1, "id_1", AME.SC("component_1"))
#     """
#     circuit = _get_circuit(circuit)
#     _ensure_mode(circuit, SKETCH_MODE)
#     ret_value = afp.set(circuit+":connect_supercomponent_port|" + "comp_aliaspath=" + comp_aliaspath +
#     ",comp_port_number=" + str(comp_port_number) + ",sc_port_id=" + sc_port_id, "")
#     return(ret_value)
# ########Ending#######################

############# SketchContentsListingFeatures #############
def AMEGetVariablesOnPort(alias_path, port_number, all_ports = False):
    """Lists the datapaths of all the parameters or variables on a port of a given submodel instance.

       (string, ...) = AMEGetVariablesOnPort(string, int)

       First argument is a string representing the alias path of the element (component or line)
       whose submodel will be set, or an AMECompLine object, as returned by AMEGetCompLine or an
       AMECompLineIteration.

       The second one corresponds with the desired port number.

       The function returns the list of datapaths.

       >>> AME.AMEGetVariablesOnPort('adherence2', 2)
       ['yOA2R0@adherence2', 'xOA2R0@adherence2']

    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return _StringListFromXML(afp.get(alias_propid + ':comp_port_list|port_number=%d,all=%d' % (port_number, all_ports)))

def AMEIsParameter(data_path):
    """Finds the element data in the current active circuit, then tells if it is a parameter.

       bool = AMEIsParameter(string)
       bool = AMEIsParameter(AMEParVar)

       The argument is either a string corresponding to the path of the data
       under the form: data_name@comp_alias_0.comp_alias_i.comp_alias_N,
       or an AMEParVar object.

       The function returns True if the tested is a parameter, False otherwise.

       >>> AME.AMEIsParameter('rp9@h2port')
       True
    """
    data_propid = make_data_property_id(*_parse_datapath(data_path))
    return bool(int(afp.get(data_propid + ":data_is_parameter")))


def AMEIsVariable(data_path):
    """Finds the element data in the current active circuit, then tells if it is a variable.

       bool = AMEIsVariable(string)
       bool = AMEIsVariable(AMEParVar)

       The argument is either a string corresponding to the variable's data path,
       in the following format: data_name@comp_alias_0.comp_alias_i.comp_alias_N

       The function returns True if the tested is a variable, False otherwise.

       >>> AME.AMEIsVariable('rp9@h2port')
       False
    """
    data_propid = make_data_property_id(*_parse_datapath(data_path))
    return bool(int(afp.get(data_propid + ":data_is_variable")))


def AMEIsLine(alias_path):
    """Finds an element from its alias path in the current active circuit then tells if it is a line.

       bool = AMEIsLine(string)
       bool = AMEIsLine(AMECompLine)

       First argument is a string representing the alias path of the element (component or line).

       It returns True if the checked element is a line, False otherwise.

       >>>AMEIsLine('control')
       True
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return bool(int(afp.get(alias_propid + ':comp_is_line')))


def AMEIsComponent(alias_path):
    """Finds an element from its alias path in the current active circuit then tells if it is a component.

       bool = AMEIsComponent(string)
       bool = AMEIsComponent(AMECompLine)

       The argument is either a string corresponding to the alias path of the
       element to check, or an AMECompLine object.

       It returns True if the checked element is a component, False otherwise.

       >>> AMEIsComponent('step')
       True
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return bool(int(afp.get(alias_propid + ':comp_is_component')))


def AMEGetVariableInfos(data_path):
    """Provides basic information about a variable which belongs to the current active circuit.

       (int, string, string, string, string) = AMEGetVariableInfos(string)

       The argument is either a string corresponding to the path of the data
       under the form: data_name@comp_alias_0.comp_alias_i.comp_alias_N, or an AMEParVar object.

       It returns None if the data path does not corresponds to a variable of
	   the current active circuit.
	   Otherwise, It returns a list containing an integer and four strings.

       The first list element is the variable dimension. 1 <= dimension <= N

       The second list element is the variable type. It can be 'ame_basic_variable',
          'ame_state_variable', or 'ame_variable_undefined'.

       The third one is the variable title.

       The fourth one is the variable unit.

       The last one is the input-output variable type, which can be 'ame_variable_io_invalid',
          'ame_variable_io_input' or 'ame_variable_io_output'

       >>> AME.AMEGetVariableInfos('VzR0@Road')
       (1, 'ame_basic_variable', '(output) : rate of climb of the ground expressed in ground frame (Galilean frame)  - Vz_R0', 'm/s', 'ame_variable_io_output')
    """
    if AMEIsVariable(data_path):
        data_propid = make_data_property_id(*_parse_datapath(data_path))
        try:
            dimension = int(afp.get(data_propid + ":data_dimension"))
        except:
            dimension = None
        type = afp.get(data_propid + ":data_type")
        title = afp.get(data_propid + ":data_title")
        try:
            unit = afp.get(data_propid + ":data_unit")
        except:
            unit = None
        io_type = afp.get(data_propid + ":data_io_type")
        return (dimension, type, title, unit, io_type)
    return None

###############################################################################
# \brief
# \version 2014-04-23 ACe 0154546:
#     Handle exception thrown by AMEGetSubmodelInfos
###############################################################################
def AMEGetAliasInfos(alias_path):
    """Provides information about the component or the line having the given alias_path
       in the current active circuit.

       (string, string, string, int, string, string) = AMEGetAliasInfos(string)

       String argument is the alias path of the component or line to check.

       First returned string gives the type of element. It is 'ame_component', 'ame_line' or 'ame_alias_undefined'.

       Second returned string gives the icon name.

       Third returned string is the name of the submodel set to the component or the line.

       Fourth returned int is the instance number of the submodel set to the component or the line.
          Note that if the current mode is other than parameter or simulation mode, the value returned will be '-1'.

       Fifth returned string is the directory the submodel belongs to.

       Sixth returned string is the category name the component or line belongs to.

       >>> AME.AMEGetAliasInfos('step')
       ('ame_component', 'step', 'STEP0', -1, '$AME/submodels', 'ctrl')
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))

    try:
      sub_name, sub_path = AMEGetSubmodelInfos(alias_path)
    except:
      sub_name, sub_path = None, None
      pass

    type = afp.get(alias_propid + ":comp_type")
    icon_name = afp.get(alias_propid + ":comp_icon_name")
    if not sub_name:
        sub_name = None
    if not sub_path:
        sub_path = None
    instance_number = int(afp.get(alias_propid + ":comp_subinstance"))
    try:
        cat_name = afp.get(alias_propid + ":comp_subcat_name")
    except:
        cat_name = None

    return (type, icon_name, sub_name, instance_number, sub_path, cat_name)

def AMEGetParametersAndVariables(alias_path):
    """Lists the datapaths of all the parameters or variables of a given submodel instance,
       specified through alias_path input argument.

       (string, ...) = AMEGetParametersAndVariables(string)
       (string, ...) = AMEGetParametersAndVariables(AMECompLine)

       The argument is either a string corresponding to the alias path of the component, or an AMECompLine object.

       The function returns the list of datapaths.

       >>> AME.AMEGetParametersAndVariables('adherence2')
       ['rgrip@adherence2', 'mumod@adherence2', 'xOA2R0@adherence2', 'yOA2R0@adherence2', 'mu@adherence2', 'refAdh@adherence2']
    """
    return _StringListFromXML(AMEGetCompParVarList(*_parse_aliaspath(alias_path)))

def AMEGetComponentsAndLines(recursive=False, circuit=None):
    """Lists the aliaspaths of all the components and lines of a given sketch in the working_circuit.

       (string, ...) = AMEGetComponentsAndLines(bool[, string])

       The first argument is a boolean which indicates if the function should go in depth within supercomponents.

       The second argument indicates the circuit in which the function will take place, the current one by default.

       The function returns the list of alias paths.

       >>> AME.AMEGetComponentsAndLines()
       ['control', 'mass1port_1', 'constant', 'control_1', 'adherence2', 'mass1port', 'spring01', 'zerospeedsource', 'Road', 'signalsink']
    """
    circuit = _get_circuit(circuit)
    ret = afp.get(circuit + ':prop=component_list|recursive=%d' % recursive)
    return _StringListFromXML(ret)

def AMEGetConnectionInformation(alias_path, port_number):
    """Provides information about what the component or the line having the
       given alias path is connected to on the given port.

       Port numbering starts at 0.

       (string, string, int) = AMEGetConnectionInformation(string, int)

       First returned string gives the connection type. It can be:
          CONNECTION_NONE, CONNECTION_COMPONENT, CONNECTION_LINE, CONNECTION_PORT
       (CONNECTION_PORT corresponds to a connection to a port label inside a
       supercomponent.)

       Second returned string is the aliaspath in case of a component or line,
       or an empty string otherwise.

       Third number is the port number on the opposite side, or 0 for an
       unconnected port.

       >>> AME.AMEGetConnectionInformation("constant_1", 0)
       ('CONNECTION_COMPONENT', 'elect01', 1)
       >>> AME.AMEGetConnectionInformation("component_1.vsine", 1)
       ('CONNECTION_PORT', '', 1)
    """
    elem_path, circuit_name = _parse_aliaspath(alias_path)
    alias_propid = make_elem_property_id(elem_path, circuit_name)

    property_id = alias_propid + ":comp_connection_information|port_number=%s" % urllib.parse.quote(str(port_number))
    connection_type, connected_aliaspath, connected_port_number = _StringListFromXML(afp.get(property_id))
    return (connection_type, connected_aliaspath, int(connected_port_number))


def AMEListAvailableSubmodels(alias_path):
    """	Returns the name and path list of available submodels for a given element.

       ((string, string),) = AMEGetAvailableSubmodels(string)

       First argument is a string representing the alias of the element.

       AMEGetAvailableSubmodel('mass2port')
       (('MAS002', '$AME/libmec/submodels'), ('MAS000', '$AME/libmec/submodels'))


       Gives the geometric details(position co-cordinates, width, height, port positions) of the component

       Output:
        - Output is a tuple containing (submodel_name, submodel_path) name and path of submodels
        ((submodel_name, submodel_path) = AMEGetComponentGeometry(string)

    """
    elem_path, circuit_name = _parse_aliaspath(alias_path)
    alias_propid = make_elem_property_id(elem_path, circuit_name)

    submodel_list = _NameAndPathListFromXML((afp.get(alias_propid + ":get_available_submodels")))

    return submodel_list

def AMEGetNumberOfPorts(alias):
    """Gives the number of ports of the component.

    (port_number) = AMEGetNumberOfPorts(string)

    input string is the alias of the component for which geometric details have to be fetched

    Output:
    - port_number is the number of ports for a given element.

    >>> AME.AMEGetNumberOfPorts('mass2port')
    2
   """

    try:
       port_number = len(AMEGetComponentGeometry(alias)[2])
    except:
       raise

    return (port_number)

def AMERunSimulation(circuit=None):
    """Starts a simulation and waits until it completes. An exception is raised
       if the simulation fails.

       >>> AMERunSimulation()
       """
    AMEStartSimulation(circuit)
    AMEWaitForSimulationEnd(circuit)

def AMEStartSimulation(circuit=None):
    """Starts a simulation but does not wait for completion.

       >>> AMEStartSimulation()
       >>> AMEIsSimulationRunning()
       True
    """
    circuit = _get_circuit(circuit)
    _ensure_mode(circuit, SIMULATION_MODE)
    afp.set(circuit + ':cmd=start_simulation', '')

def AMESetPremierSubmodel(xmlString, circuit_name=None):
    """Sets a premier sub-model to the component of the given(or the active) circuit.
       string = AMESetPremierSubmodel(xmlString, string)

       First string argument is the xml string which contains the components and corresponding submodels.
       Pass an empty string so that current category path list is considered.

       Second string argument is the circuit name.

       Returns a XML string (in form of hash) in case of any error. This hash has alias_path of component as key \
       and value is the list of error details. Empty string in case all the components are assigned with a submodel.
    """
    circuit = _get_circuit(circuit_name)
    ret = afp.set(circuit+":cmd=cmd_trigger_premier_submodel",xmlString)
    return (ret)

def AMEStopSimulation(circuit=None):
    """Stops a running simulation.

       Note that calling this function requests for the stimulation to be
       stopped, but returns immediately without waiting for the simulation to
       be finished. Use AMEWaitForSimulationEnd to be sure the simulation has
       stopped.

       >>> AMEStopSimulation()
       >>> time.sleep(3)
       >>> AMEIsSimulationRunning()
       False
    """
    circuit = _get_circuit(circuit)
    _ensure_mode(circuit, SIMULATION_MODE)
    afp.set(circuit + ':cmd=stop_simulation', '')

def AMEWaitForSimulationEnd(circuit=None):
    """Waits until there is no simulation running.

       This function returns immediately if no simulation is running. It raises
       an exception if the last simulation failed (note: even if there was no
       simulation running at the time when the function was called).

       >>> AMEStartSimulation()
       >>> AMEIsSimulationRunning()
       True
       >>> AMEWaitForSimulationEnd()
       >>> AMEIsSimulationRunning()
       False
    """
    circuit = _get_circuit(circuit)
    if afp.get(circuit + ':prop=wait_for_simulation_end') != "ok":
        raise AccessError("simulation failed or stopped")

def AMEIsSimulationRunning(circuit=None):
    """Returns True if a simulation is running, or False if there is no
       simulation running.

       >>> AMEStartSimulation()
       >>> AMEIsSimulationRunning()
       True
       >>> AMEWaitForSimulationEnd()
       >>> AMEIsSimulationRunning()
       False
    """
    circuit = _get_circuit(circuit)
    _ensure_mode(circuit, SIMULATION_MODE)
    return bool(int(afp.get(circuit + ':prop=simulation_running')))

###############################################################################
# \brief
# \version 2018-11-28 VMS CORE-10047:
#     Reimplemented using new json based way
###############################################################################
def AMESetRunParameter(parameter_name, value, circuit=None):
      """Sets a simulation parameter for the current active circuit.

      AMESetRunParameter(string, string)

      The first argument identifies the simulation parameter to set.
      The second argument is a string representing the value to set.
      The available simulation parameters, and the expected format of values are:
         - 'start_time_s': simulation start time in seconds. Floating-point number as a string.
         - 'stop_time_s': simulation stop time in seconds. Floating-point number as a string.
         - 'interval_s': simulation communication interval in seconds. Floating-point number as a string.
         - 'integ_method': integration method. "0" for standard integrator. "1" for fixed step integrator.
         - 'fixed_step_s': fixed step time in seconds. Available with fixed step integrator only. Floating-point number as a string.
         - 'fixed_integ_method': fixed step time integration method. "0" for Adams-Bashforth. "1" for Euler. "2" for Runge-Kutta.
         - 'fixed_order': order to use for Adams-Bashforth or Runge-Kutta fixed step integration method. This is a integer value: 2 <= fixed_order <= 4, encoded as a string.
         - 'max_time_step_s': maximum simulation time step in seconds. Available with standard integrator only. Floating-point number as a string.
         - 'tolerance': tolerance for convergence test. Available with standard integrator only. Floating-point number as a string.
         - (Legacy parameter) 'tolerance_s': tolerance for convergence test in seconds. Available with standard integrator only. Floating-point number as a string.
         - 'error_type': standard integration errortype. "0" for mixed error. "1" for relative error. "2" for absolute error.
         - 'solver_type': standard integration accuracy level. "0" for standard solver. "1" for cautious solver.
         - 'disable_optimized_solver': enable/disable optimized server. "0" or "False" to disable, "1" or "True" to enable.
         - 'minimal_discontinuity_handling': enable/disable the minimal discontinuity handling. "0" or "False" to disable, "1" or "True" to enable.
         - 'simulation_mode': simulation mode. "1" for stabilizing run. "2" for dynamic run. "3" for stabilizing run followed by dynamic run.
         - 'discontinuity_printout': enable/disable discontinuity printout. This is a dynamic run option. "0" or "False" to disable, "1" or "True" to enable.
         - 'activity_calculation': enable/disable activity index calculation for dynamic run. "0" or "False" to disable, "1" or "True" to enable.
         - 'power_calculation': enable/disable power calculation for dynamic run. "0" or "False" to disable, "1" or "True" to enable.
         - 'energy_calculation': enable/disable energy calculation for dynamic run. "0" or "False" to disable, "1" or "True" to enable.
         - 'hold_inputs_constant': enable/disable the hold inputs constant dynamic run option. "0" or "False" to disable, "1" or "True" to enable.
         - 'lock_non_propagating_state': lock/unlock non propagating states for stabilizing run. "0" or "False" to disable, "1" or "True" to enable.
         - 'diagnotics': enable/disable stabilizing run diagnostics. "0" or "False" to disable, "1" or "True" to enable.
         - 'run_type': run type. "0" for single run, "1" for batch.
         - 'continuation_run': enable/disable the continuation run option. "0" or "False" to disable, "1" or "True" to enable

      The encoding of floating-point numbers as strings must be the one expected by the C 'atof' function.
      It should be compatible with the result of str() builtin applied to Python floating-point numbers.

      >>> ame_apy.AMESetRunParameter('stop_time_s', '18')
      """
      if value == "True":
          value = "1"
      elif value == "False":
          value = "0"
      return _AME.AMESetRunParameter(**locals())

def AMEGetRunParameter(parameter_name, circuit=None):
      """Provides the value of one simulation parameter of the current active circuit.\n"

      string = AMEGetRunParameter(string)

      The string argument identifies the parameter to get.
      The return value is a string encoding the value, or None if the parameter identifier is unknown.
      The available simulation parameters, and the corresponding return value format are:
         - 'start_time_s': simulation start time in seconds. Floating-point number as a string.
         - 'stop_time_s': simulation stop time in seconds. Floating-point number as a string.
         - 'interval_s': simulation communication interval in seconds. Floating-point number as a string.
         - 'integ_method': integration method. "0" for standard integrator. "1" for fixed step integrator.
         - 'fixed_step_s': fixed step time in seconds. Available with fixed step integrator only. Floating-point number as a string.
         - 'fixed_integ_method': fixed step time integration method. "0" for Adams-Bashforth and Euler. "2" for Runge-Kutta.
            See 'fixed_order' for differentiating between Adams-Bashforth and Euler.
         - 'fixed_order': order to use for Adams-Bashforth or Runge-Kutta fixed step integration method. This is a integer value: 2 <= fixed_order <= 4, encoded as a string.
            If 'fixed_integ_method' is Adams-Bashforth and the order is "1", then the integration method is in fact Euler.
         - 'max_time_step_s': maximum simulation time step in seconds. Available with standard integrator only. Floating-point number as a string.
         - 'tolerance_s': tolerance for convergence test in seconds. Available with standard integrator only. Floating-point number as a string. Legacy parameter.
         - 'tolerance': tolerance for convergence test. Available with standard integrator only. Floating-point number as a string.
         - 'error_type': standard integration errortype. "0" for mixed error. "1" for relative error. "2" for absolute error.
         - 'solver_type': standard integration accuracy level. "0" for standard solver. "1" for cautious solver.
         - 'disable_optimized_solver': enable/disable optimized server. "0" for disabled, "1" for enabled.
         - 'minimal_discontinuity_handling': enable/disable the minimal discontinuity handling. "0" for disabled, "1" for enabled.
         - 'simulation_mode': simulation mode. "1" for stabilizing run. "2" for dynamic run. "3" for stabilizing run followed by dynamic run.
         - 'discontinuity_printout': enable/disable discontinuity printout. This is a dynamic run option. "0" for disabled, "1" for enabled.
         - 'activity_calculation': enable/disable activity index calculation for dynamic run. "0" for disabled, "1" for enabled.
         - 'power_calculation': enable/disable power calculation for dynamic run. "0" for disabled, "1" for enabled.
         - 'energy_calculation': enable/disable energy calculation for dynamic run. "0" for disabled, "1" for enabled.
         - 'hold_inputs_constant': enable/disable the hold inputs constant dynamic run option. "0" for disabled, "1" for enabled.
         - 'lock_non_propagating_state': lock/unlock non propagating states for stabilizing run. "0" for disabled, "1" for enabled.
         - 'diagnotics': enable/disable stabilizing run diagnostics. "0" for disabled, "1" for enabled.
         - 'run_type': run type. "0" for single run, "1" for batch.
         - 'continuation_run': continuation run option status. "0" for disabled, "1" for enabled

      The encoding of floating-point numbers as strings is the one given by the C 'printf' function with the %25.14e format.
      It should be compatible with the float() Python builtin.

      >>> ame_apy.AMEGetRunParameter('stop_time_s')
      '1.80000000000000e+001'
      """
      document = _get_document(circuit)
      _ensure_mode(document, SIMULATION_MODE)
      circuit_propid = make_circuit_property_id(document, CIR_RUN_PARAMETER)
      return afp.get(circuit_propid + "|run_parameter_name=" + urllib.parse.quote(parameter_name))

# Embedded batch API
class Struct(dict):
   def __init__(self, **kwargs):
      super(Struct, self).__init__(**kwargs)
      self.__dict__ = self

BATCH = enum(RANGE='RANGE', SET='SET')
SIMULATION_TYPE = enum(BATCH='BATCH', SINGLE='SINGLE')

BATCH_EXCEPTION = enum(INVALID_CIRCUIT='INVALID_CIRCUIT', \
   INVALID_DATAPATH='INVALID_DATAPATH', INVALID_BATCH_METHOD='INVALID_BATCH_METHOD', \
   INVALID_OPERATION='INVALID_OPERATION', INVALID_NEW_VALUE='INVALID_NEW_VALUE', \
   INVALID_SET_NUMBER='INVALID_SET_NUMBER')

TYPE = 'type'
NAME = 'name'
SET = 'set'
VALUE = 'value'
STEP = 'step'
BELOW = 'below'
ABOVE = 'above'


def AMESetSimulationType(sim_type,batch=None,circuit=None):
   ''' It sets the simulation type for the circuit.

      Type can be either 'BATCH' for batch runs or
      'SINGLE' for single runs.

      batch is a list of batch runs that we want to run.

      It will return error if we set type as 'SINGLE' and
      pass a list of batches to be run.

      If we set type as 'BATCH' and don't send any batch list
      then it will run all the batches.

      >>> AME.AMESetSimulationType(SIMULATION_TYPE.BATCH,1)
      >>> AME.AMESetSimulationType(SIMULATION_TYPE.BATCH,[3,5])
   '''
   circuit = _get_circuit(circuit)
   value = ''
   if sim_type is SIMULATION_TYPE.SINGLE and batch is not None:
      raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
      return None
   if batch is not None:
      batch_str = []
      batch_list = []
      if type(batch) is list:
         batch_list = batch
      elif type(batch) is int:
         batch_list.append(batch)
      else:
         raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
      for i in batch_list:
         batch_str.append(str(i))
      value = _StringListToXML(batch_str)
   ret_val = afp.set(circuit + ":cmd=ame_set_simulation_type|action=set_simulation", sim_type + ',' + value)
   return ret_val

def AMEGetBatchRuns(circuit=None):
   ''' This API gets the list of successful last
      batch runs for a circuit.

      >>> AME.AMEGetBatchRuns()
      ['1','2','5','8']
   '''
   circuit = _get_circuit(circuit)
   ret = afp.get(circuit + ":cmd=ame_get_batch_last_run")
   if not ret:
      return []
   return _StringListFromXML(ret)

def AMECreateBatch(batch_type):
   ''' It returns a newly created batch. A batch type can be either
      a 'SET' or a 'RANGE' type.

      >>> AME.AMECreateBatch(BATCH.SET)
   '''
   if batch_type is BATCH.SET or batch_type is BATCH.RANGE:
      return Struct(type = batch_type, param = [])
   else:
      raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)

def AMEBatchCreateParam(data_path,data_dict):
   ''' It creates a batch parameter and returns the same.

      data_path is the data path of the parameter which is
      used as batch parameter

      data_dict is the set of values
      to be set for that param.

      If we are creating a param for the batch of type 'SET',
      then dict should have a set of values

      >>> AME.AMEBatchCreateParam(data_path,{'set':[val1,val2]})

      If we are creating a param of type 'RANGE', then we need to
      pass 'step,'value',above' and 'below'

      >>> AME.AMEBatchCreateParam(data_path,
         {'step':val1,'value':val2,'below':val3,'above':val4})

      It has to be either STEP or RANGE. It cannot be both or neither.

      For RANGE, all the four arguments inside dict are necessary.
   '''
   if not isinstance(data_path, six.string_types):
      raise AccessError(BATCH_EXCEPTION.INVALID_DATAPATH)
   if type(data_dict) is not dict:
      raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
   if (SET in data_dict) and ((VALUE in data_dict) or (ABOVE in data_dict) or (BELOW in data_dict) or (STEP in data_dict)):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   if (SET in data_dict):
      return Struct(name=data_path,set=data_dict[SET])
   elif ((VALUE in data_dict) and (ABOVE in data_dict) and (BELOW in data_dict) and (STEP in data_dict)):
      value= data_dict[VALUE]
      below = data_dict[BELOW]
      above = data_dict[ABOVE]
      step = data_dict[STEP]
      return Struct(name=data_path,value=value,below=below,above=above,step=step)
   else:
      raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)

def AMEBatchAddSet(batch,number_of_sets=1):
   ''' It adds sets to a given batch.
      The batch should be of type 'SET', else it will return error

      number_of_sets should be an integer >= 0.

      By default number_of_sets is 1.

      Calling AMEBatchAddSet with number_of_sets = 0
      will not make any difference in sets of batch.

      >>> AME.AMEBatchAddSet(batch,10)

   '''
   if not _IsValidBatch(batch) or batch.type is not BATCH.SET or number_of_sets < 0:
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   for i in range(0,number_of_sets):
      for inner in range(0,len(batch.param)):
         batch.param[inner].set.append([])

def AMEBatchGetNSets(batch):
   ''' It will return the number of sets in the batch

      Batch should be type of SET, else it will raise error.

      >>> no_of_bat = AME.AMEBatchGetNSets(batch)

   '''
   if not _IsValidBatch(batch) or batch.type is not BATCH.SET:
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   no_of_set = 0
   if len(batch.param) > 0:
      no_of_set = len(batch.param[0].set)
   return no_of_set

def AMEBatchGetNParams(batch):
   ''' It returns number of parameters in the batch.

      >>> no_of_params = AME.AMEBatchGetNParams(batch)

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   return len(batch.param)

def AMEBatchGetNRuns(batch):
   ''' It returns the total number of runs for a given batch.

      If batch is of type 'SET', then number of expected runs is
      same as AMEBatchGetNSets

      >>> no_of_runs = AME.AMEBatchGetNRuns(batch)

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   if len(batch.param) <= 0:
      return 0
   if batch.type is BATCH.SET:
      return AMEBatchGetNSets(batch)
   elif batch.type is BATCH.RANGE:
      total_runs = 1
      for i in range(0,len(batch.param)):
         total_runs = total_runs * (1 + batch.param[i].above + batch.param[i].below )
      return total_runs
   raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)

def AMEBatchGetParam(batch,param):
   ''' It returns a parameter specified by parameter name or parameter position.

      Parameter name is the data path of the parameter.

      Parameter position starts from 1.

      >>param_at_2 = AME.AMEBatchGetParam(batch,2)
      >>param_mass = AME.AMEBatchGetParam(batch,'mass@mass1port')

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   no_of_params = len(batch.param)
   if no_of_params <= 0:
      raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
   found = IsParamInBatch(batch,param)
   if found >= 0:
      return batch.param[found]
   return None

def AMEBatchRemoveParam(batch,param):
   ''' It will remove the given parameter(s) from the batch.

      Param can be a single parameter or list of parameter,
      single param name or list of param names, single param
      index or list of indexes.

      >> AME.AMEBatchRemoveParam(batch,param1)
      >> AME.AMEBatchRemoveParam(batch,[param1,param2,param3])
      >> AME.AMEBatchRemoveParam(batch,'mass@mass1port')
      >> AME.AMEBatchRemoveParam(batch,['mass@mass1port',
            'mass@mass2port','theta@mass1port'])
      >> AME.AMEBatchRemoveParam(batch,1)
      >> AME.AMEBatchRemoveParam(batch,[1,3,5])

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   delete_list = []
   param_list = []
   if type(param) is list:
      param_list = param
   else:
      param_list.append(param)
   for local_param in param_list:
      if isinstance(local_param, basestring) or isinstance(local_param, int):
         found = IsParamInBatch(batch,local_param)
         if found >= 0 :
            delete_list.append(batch.param[found])
      elif type(local_param) is Struct:
         if local_param in batch.param:
            delete_list.append(local_param)
      else:
         raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
   for del_param in delete_list:
      batch.param.remove(del_param)

def AMEBatchRemoveSet(batch, set_no_list):
   ''' It removes set(s) from the batch.

       set_no_list can be a single set index or list of set indexes.

       >> AME.AMEBatchRemoveSet(batch,set_no)
       >> AME.AMEBatchRemoveSet(batch,[set_no1,set_no2,set_no3])

   '''
   if not _IsValidBatch(batch) or batch.type is BATCH.RANGE or len(batch.param) <= 0:
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   delete_sets = []
   len_of_set = len(batch.param[0].set)
   if type(set_no_list) is list:
      delete_sets = set_no_list
   else:
      delete_sets.append(set_no_list)
   delete_sets.sort()
   for set in delete_sets:
      if not (set > 0 and set <= len_of_set):
         raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
   for par_len in range(0,len(batch.param)):
      for set in reversed(delete_sets):
         del batch.param[par_len].set[set-1]

def AMEBatchPutParam(batch,param):
   ''' It will append param(s) to the given batch.

      Param can be either a single parameter or list of parameters.

      >> AME.AMEBatchPutParam(batch,param1)
      >> AME.AMEBatchPutParam(batch,[param1,param2,param3])

   '''
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   param_list = []
   if type(param) is list:
      param_list = param
   else:
      param_list.append(param)
   for par in param_list:
      if batch.type is BATCH.SET and hasattr(par, VALUE):
         raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
      elif batch.type is BATCH.RANGE and hasattr(par, SET):
         raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
      if par in batch.param:
         continue
      if batch.type is BATCH.SET:
         if len(batch.param) > 0:
            if batch.param[0].set is not None and par.set is not None:
               if len(batch.param[0].set) != len(par.set):
                  raise AccessError(BATCH_EXCEPTION.INVALID_OPERATION)
            else:
               raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   for par in param_list:
      batch.param.append(par)

def AMEGetBatch(circuit = None):
   """Gets the Batch for the given circuit.

      Batch = AMEGetBatch()

      Returns the batch structure for the give circuit.

      >>> AME.AMEGetBatch()
      ''
   """
   circuit = _get_circuit(circuit)
   xml_str = afp.get(circuit + ':cmd=batch_api|action=get_batch')
   return _xml2dict_batch(ET.fromstring(xml_str))

def AMEPutBatch(batch, circuit = None):
   """Sets the batch structure to the given Circuit.

      >>> AME.AMEPutBatch(batch)

      If the batch is of type RANGE,
      Below and Above have to be an integer >= 0
      else this API will return error.

      There should not be any text parameter
      in batch as RANGE type does not support
      Text Parameters.
   """
   if not _IsValidBatch(batch):
      raise AccessError(BATCH_EXCEPTION.INVALID_BATCH_METHOD)
   circuit = _get_circuit(circuit)
   if sys.version_info[0] < 3:
      ret_val = afp.set(circuit + ":cmd=batch_api|action=set_batch", ET.tostring(_dict2xml_batch(batch)))
   else:
      ret_val = afp.set(circuit + ":cmd=batch_api|action=set_batch", ET.tostring(_dict2xml_batch(batch), encoding='unicode'))



def GetCompNameFromErrorCode(xmltext):
  tree = ET.fromstring(xmltext)
  error_data = []
  for child in tree.getchildren():
     if child.tag == 'COMPONENT':
         error_data.append(child.attrib['NAME'])
  return error_data

def GetErrorDescrFromErrorCode(xmltext):
  tree = ET.fromstring(xmltext)
  error_data = []
  for child in tree.getchildren():
     if child.tag == 'COMPONENT':
         for childIntr in child.getchildren():
             if childIntr.tag == 'SUBMODEL':
                 error_data.append(childIntr.attrib['PATH'])
  return error_data

def AMEGetGlobalParameterUniqueName(data_path):
   """This method returns the unique name of the global parameter given by argument. If this
      global is local to a supercomponent the unique name will contain the name of the
      supercomponent, else the unique name and the data path will be equivalent.

      string = AMEGetGlobalParameterUniqueName(string)

      The argument is a string corresponding to the path of the
      parameter given under the form:
          parameter_name@comp_alias_0.comp_alias_i.comp_alias_N,

      Returns a string, the global parameter unique name.

      >>> AME.AMEGetGlobalParameterUniqueName('force0@springdamper01')
      'force0__springdamper01_1'

   """
   data_propid = make_data_property_id(*(_parse_datapath(data_path)))
   return afp.get(data_propid + ':testapi_scp_unique_name')

def AMEChangeMode(mode, circuit=None):
   """Tries to set the current mode for the given circuit.
   Will raise ModeChangeError on failure.

   AMEChangeMode(string, string)

   First argument is the mode name. It can be:
   - 'sketch_mode' (or SKETCH_MODE)
   - 'submodel_mode' (or SUBMODEL_MODE)
   - 'parameter_mode' (or PARAMETER_MODE)
   - 'simulation_mode' (or SIMULATION_MODE)

   The second argument is the circuit name. It is optional. If None, then the current active circuit name is used.

   Example:
   >>> AMEChangeMode('sketch_mode')

   """
   circuit_name = _get_circuit(circuit)
   current_mode = AMEGetMode(circuit)
   if (current_mode != mode):
      _change_mode(circuit_name, mode)


INVALID_GP_TYPE_ERR_STR = 'INVALID_GP_TYPE'
INVALID_ENUM_VALUE = 'INVALID_ENUM_VALUE'
INVALID_EXPOSED_TITLE = 'INVALID_EXPOSED_TITLE'
INVALID_EXPOSED_GROUP_NAME = 'INVALID_EXPOSED_GROUP_NAME'

COMMON_ERROR_CODES = ["INVALID_DATAPATH", "INVALID_PARENT_GROUP_ID", "INVALID_POSITION", "INVALID_CIRCUIT", "INVALID_SC_CIRCUIT"]

GLOBAL_PARAM_ERROR_CODES = ["INVALID_GLOBAL_PARAM_NAME", "INVALID_GP_GROUP_ID", "CANNOT_FIND_GLOBAL_PARAM", \
   "CANNOT_FIND_GP_GROUP", "GROUP_CANNOT_BE_MOVED_INSIDE_ITS_CHILD", "INVALID_GP_GROUP_NAME"]

EXPOSED_PARAM_VAR_ERROR_CODES = ["INVALID_EXPOSED_PARAM_NAME", "INVALID_VISIBILITY_EXPRESSION", \
    "INVALID_EXPOSED_GROUP_ID", "CANNOT_APPLY_INPUT", "CANNOT_FIND_EXPOSED_ITEM", "CANNOT_FIND_EXPOSED_GROUP"]

def raiseGlobalOrExposedParamErrorIfAny(return_code):
   if(len(return_code) > 0 and (return_code in COMMON_ERROR_CODES or return_code in GLOBAL_PARAM_ERROR_CODES or \
   return_code in EXPOSED_PARAM_VAR_ERROR_CODES)):
      raise AccessError(return_code)

# Global parameter APIs

def AMEGetGlobalParamsList(sc_alias_path = None):
    """Gets the list of all global parameters in the active circuit.

       [string, string, string, ... , string] = AMEGetGlobalParamsList(string)

       First string argument is alias path of the supercomponent from which the list
       of global parameters will be obtained. If ignored, active supercomponent circuit will be considered.

       Returns a list of names of all the global parameters in the given circuit.

       >>> AME.AMEGetGlobalParamsList('component_3')
       >>> ['gp_name_1', 'gp_name_2', 'gp_name_3', 'gp_name_4']
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    ret = None
    try:
       ret = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_global_params_list")
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

    gp_list = _StringListFromXML(ret)
    return gp_list

def AMEAddGlobalParameter(gp_type, name = None, title = None, value = None, enumeration_values = None, \
   parent_group_id = None, position = None, sc_alias_path = None, gp_unit = None):
    """Creates a global parameter in the active circuit.

       string = AMEAddGlobalParameter(int, string, string, string, string_list, string, int, string)

       First string argument is the type of the global parameter.
       1- Real, 2-Integer, 3-Text and 4-Enum

       Second string argument is the name of the global parameter.
       If ignored, default name will be set.

       Third string argument is the title of the global parameter.
       If ignored, default title will be set.

       Fourth string argument is the value of the global parameter.
       If ignored, default value will be set. For Enumeration GP, the value is case-sensitive.

       Fifth string_list argument is list of enumeration values to be used
       in case of enumeration global parameter. If ignored, the enumeration list
       of the enumeration global parameter will not be constructed.

       Sixth string argument is ID of the parent group in which this global parameter
       is to be added. If ignored, the global parameter will be added to top level.

       Seventh integer argument is position of this global parameter in its parent/root.
       If ignored, the global parameter will be appended at last under its parent.

       Eighth string argument is alias path of the supercomponent in which we are going to
       create global parameter. If ignored, active circuit will be considered.
       
       Ninth string argument is the unit of the global parameter.
       If ignored, default unit will be set.
       
       Returns the name of the newly created global parameter

       >>> AME.AMEAddGlobalParameter(1, 'real_gp', 'new_title', '23.5', None, 'gp_folder_4', 3, 'component_1')
       'real_gp'
       >>> AME.AMEAddGlobalParameter(2, 'int_gp', 'new_title', '11', None, None, 4, 'component_2.component_3')
       'real_gp'
       >>> AME.AMEAddGlobalParameter(3, 'text_gp', 'new_title', 'amesim', None, 'parent_group_2', None, 'component_4')
       'real_gp'
       >>> AME.AMEAddGlobalParameter(4, 'enum_gp', 'new_title', 'Rectangle', ['Rectangle', 'Circle', 'Triangle'], \
       'gp_folder_1', 1, 'component_2')
       'enum_gp'
       >>> AME.AMEAddGlobalParameter(1, 'gp_new', 'titlenew', '11', None, None, None, None, 'm/s')
       'gp_new'
    """    
    return _AME.AMEAddGlobalParameter(**locals())

def AMECreateGlobalParameterFromDataPath(data_path, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates a global parameter from submodel parameter in the active circuit.
       This is equivalent to drag-dropping a submodel parameter from contextual view to
       global parameters dialog.

       string = AMECreateGlobalParameterFromDataPath(string, string, int, string)

       First string argument is the data path of the submodel parameter.

       Second string argument is ID of the parent group under which this global parameter
       is to be added. If ignored, the global parameter will be added to top level.

       Third integer argument is position of this global parameter under its parent/root.
       If ignored, the global parameter will be appended at last under its parent.

       Fourth string argument is alias path of the supercomponent in which we are going to
       create global parameter. If ignored, active circuit will be considered.

       Returns the name of the newly created global parameter.

       >>> AME.AMECreateGlobalParameterFromDataPath('param@component', 'gp_folder', 1, 'component_1.component_2')
       'gp_name'
    """
    if(data_path is None or len(data_path) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[3])
    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, SUBMODEL_MODE)

    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_global_param_from_data_path", data_path + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMECreateGPGroup(group_name = None, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates a GP group in the active circuit.

       string = AMECreateGPGroup(string, string, int, string)

       First string argument is the name of the GP group to be set.
       If ignored, default name will be set to the GP group.

       Second string argument is ID of the parent group under which this GP group
       is to be added. If ignored, the GP group will be added to top level.

       Third integer argument is position of this GP group in its parent/root.
       If ignored, the GP group will be appended at last.

       Fourth string argument is alias path of the supercomponent in which we are going to
       create global parameter group. If ignored, active circuit will be considered.

       Returns the ID of the newly created GP group.

       >>> AME.AMECreateGPGroup('mechanical_folder', 'gp_folder_2', 0, 'component_2')
       'gp_folder_1'
    """
    if(group_name is None):
       group_name = str("")
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_GP_group", group_name + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMERemoveGlobalParameter(gp_name, sc_alias_path = None):
    """Deletes a global parameter from the active circuit.

       AMERemoveGlobalParameter(string, string)

       First string argument is the name of the global parameter to be deleted.

       Second string argument is alias path of the supercomponent from which we are going to
       remove global parameter. If ignored, active circuit will be considered.

       >>> AME.AMERemoveGlobalParameter('real_index_gp', 'component_2.component_3')
    """
    if (gp_name is None or len(gp_name) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_global_param", gp_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEDeleteGPGroup(group_id, sc_alias_path = None):
    """Deletes a global parameter folder from the active circuit.

       AMEDeleteGPGroup(string, string)

       First string argument is the ID of the GP group to be deleted.

       Second string argument is alias path of the supercomponent from which we are going to
       remove global parameter group. If ignored, active circuit will be considered.

       >>> AME.AMEDeleteGPGroup('gp_folder_3', 'component_3')
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[1])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_GP_group", group_id)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMESetGPLocation(gp_name, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a global parameter in the active circuit.

       AMESetGPLocation(string, string, int, string)

       First string argument is the name of the global parameter.

       Second string argument is ID of the parent GP group under which this global parameter
       is to be added. If None is passed, the global parameter will be added to top level.

       Third integer argument is position of this global parameter in its parent/root.
       If None is passed, the global parameter will be appended at last.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active circuit will be considered.

       >>> AME.AMESetGPLocation('mass_gp', 'gp_folder_5', 1, 'component_1.component_2')
    """
    if (gp_name is None or len(gp_name) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)

    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_global_param_location", gp_name + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetGPLocation(gp_name, sc_alias_path = None):
    """Gets the location of a GP group in the active circuit.

       (string, int) = AMEGetGPLocation(string, string)

       First string argument is the name of the global parameter.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active circuit will be considered.

       Returns a tuple - ID of parent GP group and position in its parent.

       >>> AME.AMEGetGPLocation('mass_gp', None)
       >>> ('gp_folder_4', 7)
	   >>> AME.AMEGetGPLocation('inclination_gp', None)
	   >>> ('[TOP LEVEL GLOBAL PARAM]', 3)
    """
    circuit_name = _get_circuit(None)

    if (gp_name is None or len(gp_name) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_global_param_location|gp_name=%s" % gp_name))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetGPGroupLocation(group_id, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a GP group in the active circuit.

       AMESetGPGroupLocation(string, string, int, string)

       First string argument is the ID of the GP group.

       Second string argument is ID of the parent group under which this GP group
       is to be added. If None is passed, the GP group will be added to top level.

       Third integer argument is position of this GP group in its parent/root.
       If None is passed, the GP group will be appended at last under its parent.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active circuit will be considered.

       >>> AME.AMESetGPGroupLocation('mass_gp', 'gp_folder_5', 1, None)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[1])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_GP_group_location", group_id + ','+ \
          parent_group_id + ',' + str(position))

       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetGPGroupLocation(group_id, sc_alias_path = None):
    """Gets the location of a GP group in the active circuit.

       (string, int) = AMEGetGPGroupLocation(string, string)

       First string argument is the ID of the GP group.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active circuit will be considered.

       Returns a tuple - ID of parent GP group and position in its parent.

       >>> AME.AMEGetGPGroupLocation('gp_folder_5', None)
       >>> ('gp_folder_4', 7)
       >>> AME.AMEGetGPGroupLocation('gp_folder_1', None)
	   >>> ('[TOP LEVEL GP GROUP]', 3)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[1])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_GP_group_location|group_id=%s" % group_id))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetGPGroupName(group_id, new_name, sc_alias_path = None):
    """Sets the name of a GP group in the active circuit.

       AMESetGPGroupName(string, string, string)

       First string argument is the ID of the GP group.

       Second string argument is ID of the GP group.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active circuit will be considered.

       >>> AME.AMESetGPGroupName('gp_folder_5', 'new_folder_name', None)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[1])
    if (new_name is None or len(new_name) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[5])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_GP_group_name", group_id + ','+ new_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetGPGroupsList(sc_alias_path = None):
    """Gets the list of all GP groups in the active circuit.

       [(string, string), (string, string), ..., (string, string)] = AMEGetGPGroupsList(string)

       First string argument is alias path of the supercomponent from which the list
       of global parameter groups will be obtained. If ignored, active circuit will be considered.

       Returns a list of tuple of group ID and group name of all the GP groups in the given circuit

       >>> AME.AMEGetGPGroupsList(None)
       >>> [('gp_folder_1', 'foldler_name_1'), ('gp_folder_2', 'foldler_name_2'), ('gp_folder_3', 'foldler_name_3')]
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    try:
       tree = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_GP_groups_list")
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    tuple_list = _TupleListFromXML(tree)
    return (tuple_list)

# Exposed parameter APIs

def AMECreateExposedParamFromDataPath(data_path, exposed_name = None, exposed_title = None, \
    parent_group_id = None, position = None, sc_alias_path = None):
    """Creates an exposed parameter from submodel parameter in the active circuit.

       string = AMECreateExposedParamFromDataPath(string, string, string, string, int, string)

       First string argument is the data path of the submodel parameter.

       Second string argument is the exposed name of the exposed parameter.
       If ignored, default exposed name will be set.

       Third string argument is the exposed title of the exposed parameter.
       If ignored, default exposed title will be set.

       Fourth string argument is ID of the parent group in which this exposed parameter
       is to be added. If ignored, the exposed parameter will be added to top level.

       Fifth integer argument is position of this exposed parameter in its parent/root.
       If ignored, the exposed parameter will be appended at last.

       Sixth string argument is alias path of the supercomponent in which we are going to
       expose parameter. If ignored, active supercomponent circuit will be considered.

       Returns the datapath of the newly created exposed parameter.

       >>> AME.AMECreateExposedParamFromDataPath('param@component_1.mass_1_port', 'exposed_name', 'exposed_title', \
	   'custom_exposed_folder_2', 1, 'component_2')
       'param@component_1'

       Known limitations:
        - we can't expose a global parameter local to the supercomponent
    """
    if (data_path is None or len(data_path) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if exposed_name is None:
       exposed_name = str("")
    if exposed_title is None:
       exposed_title = str("")
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)

    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_param_from_data_path", data_path + ',' + \
          exposed_name + ',' + exposed_title + ',' + parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMECreateExposedParamFromGP(gp_name, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates an exposed parameter from global parameter in the active circuit.

       string = AMECreateExposedParamFromGP(string, string, int, string)

       First string argument is the name of the global parameter.

       Second string argument is ID of the parent group in which this exposed parameter
       is to be added. If ignored, the exposed parameter will be added to top level.

       Third integer argument is position of this exposed parameter in its parent/root.
       If ignored, the exposed parameter will be appended at last under its parent.

       Fourth string argument is alias path of the supercomponent in which we are going to
       expose parameter. If ignored, active supercomponent circuit will be considered.

       Returns the datapath of the newly created exposed parameter.

       >>> AME.AMECreateExposedParamFromGP('local_gp_1', 'custom_exposed_folder', 3, 'component_1')
       'local_gp_1@component_1'
    """
    if (gp_name is None or len(gp_name) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_param_from_gp", gp_name + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMECreateExposedParamGroup(group_name = None, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates a exposed parameter group in the active circuit.

       string = AMECreateExposedParamGroup(string, string, int, string)

       First string argument is the name of the exposed parameter group.
       If ignored, a default name will be set to the group.

       Second string argument is ID of the parent group in which this exposed parameter group
       is to be added. If ignored, the exposed parameter group will be added to top level.

       Third integer argument is position of this exposed parameter group in its parent/root.
       If ignored, the exposed parameter group will be appended at last.

       Fourth string argument is alias path of the supercomponent in which we are going to create the
       expose parameter group. If ignored, active supercomponent circuit will be considered.

       Returns the ID of the newly created exposed parameter group.

       >>> AME.AMECreateExposedParamGroup('mechanical_folder', 'custom_exposed_folder_3', 4, 'component_2')
       'custom_exposed_folder_5'
    """
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if(group_name is None):
       group_name = str("")
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_param_group", group_name + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMECreateExposedParamGroupFromGPGroup(gp_group_id, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates an exposed parameter group from GP group in the active circuit.

       string = AMECreateExposedParamGroupFromGPGroup(string, string, int, string)

       First string argument is the ID of the global parameter group.

       Second string argument is ID of the parent group in which this exposed parameter group
       is to be added. If ignored, the exposed parameter will be added to top level.

       Third integer argument is position of this exposed parameter in its parent/root.
       If ignored, the exposed parameter will be appended at last.

       Fourth string argument is alias path of the supercomponent in which we are going to
       expose parameter group. If ignored, active supercomponent circuit will be considered.

       Returns the ID of the newly created exposed parameter group.

       >>> AME.AMECreateExposedParamGroupFromGPGroup('custom_gp_group_2', 'custom_exposed_folder_2', 0, 'component_3')
       'custom_exposed_folder_8'
    """
    if(gp_group_id is None or len(gp_group_id) == 0):
       raise AccessError(GLOBAL_PARAM_ERROR_CODES[1])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_param_group_from_gp_group", gp_group_id + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMEDeleteExposedParam(exposed_datapath, sc_alias_path = None):
    """Deletes a exposed parameter from the active circuit.

       AMEDeleteExposedParam(string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is alias path of the supercomponent from which we are going to
       delete an expose parameter. If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEDeleteExposedParam('pressure@component_2', 'component_2')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_exposed_param", exposed_datapath)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEDeleteExposedParamGroup(group_id, sc_alias_path = None):
    """Deletes a exposed parameter group from the active circuit.

       AMEDeleteExposedParamGroup(string, string)

       First string argument is the Id of the exposed parameter group.

       Second string argument is alias path of the supercomponent from which we are going to
       delete an expose parameter group. If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEDeleteExposedParamGroup('custom_exposed_folder', 'component_1')
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)

    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_exposed_param_group", group_id)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMESetExposedParamName(exposed_datapath, new_exposed_name, sc_alias_path = None):
    """Sets the name of a exposed parameter in the active circuit.Returns
	   the new datapath of the exposed parameter.

       string = AMESetExposedParamName(string, string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is the new exposed name to be set.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

	   Returns the new datapath of the exposed parameter

       >>> AME.AMESetExposedParamName('exp_mass@component_3', 'new_mass', 'component_2')
	   >>>'new_mass@component_3'
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_name", exposed_datapath + ','+ new_exposed_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

    return ret

def AMEGetExposedParamsList(sc_alias_path = None):
    """Gets the list of all exposed parameters in the active circuit.

       [string, string, string, ... , string] = AMEGetExposedParamsList(string)

       First string argument is alias path of the supercomponent from which the list
       of exposed parameters will be obtained. If ignored, active supercomponent circuit will be considered.

       Returns a list of data path of all the exposed parameters in the given circuit.

       >>> AME.AMEGetExposedParamsList('component_1')
       >>> ['resistance@component_1', 'capacitance@component_1', 'inductance@component_1']
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_params_list")
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    tuple_list = _TupleListFromXML(tree)
    return (tuple_list)

def AMESetExposedParamTitle(exposed_datapath, new_exposed_title, sc_alias_path = None):
    """Sets the title of an exposed parameter in the active circuit.

       AMESetExposedParamTitle(string, string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is the new exposed title to be set.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedParamTitle('srate@component_1', 'new_title', 'component_1')
    """
    if(new_exposed_title is None or len(new_exposed_title) == 0):
       raise AccessError(INVALID_EXPOSED_TITLE)
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_title", exposed_datapath + ','+ new_exposed_title)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedParamTitle(exposed_datapath, sc_alias_path = None):
    """Gets the exposed title of an exposed parameter in the active circuit.

       string = AMESetExposedVarTitle(string, string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEGetExposedParamTitle('param@component_2', 'component_2')
       >>> 'initial displacement'
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_param_title|data_path=%s" % exposed_datapath)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return ret

def AMEValidateVisibilityExpression(exposed_datapath, new_visibility_expr, sc_alias_path = None):
    """Validates the visibility expression of an exposed global parameter in the active circuit.

       bool = AMEValidateVisibilityExpression(string, string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is the visibility expression to be validated.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the validity of the given visibility expression.

       >>> AME.AMEValidateVisibilityExpression('real_gp@component_1', 'param1-param3', 'component_1')
       >>> True
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if (new_visibility_expr is None or len(new_visibility_expr) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[1])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=validate_visibility_expr|data_path=%s,visibility_expr=%s" % \
       (exposed_datapath, new_visibility_expr))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    if(len(ret) == 0):
       return True
    else:
       return False

def AMESetExposedParamVisibilityExpr(exposed_datapath, new_visibility_expr, sc_alias_path = None):
    """Sets the visibility expression of an exposed global parameter in the active circuit.

       AMESetExposedParamVisibilityExpr(string, string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is the new visibility expression to be set.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedParamVisibilityExpr('custom_exposed_folder_5', 'mass > 2.5', 'component_4')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if (new_visibility_expr is None or len(new_visibility_expr) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[1])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_visibility_expr", exposed_datapath +\
       ','+ new_visibility_expr)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedParamVisibilityExpr(exposed_datapath, sc_alias_path = None):
    """Gets the visibility expression of an exposed parameter in the active circuit.

       string = AMEGetExposedParamVisibilityExpr(string, string)

       First string argument is the datapath of the exposed parameter.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the visibility expression of the given exposed parameter.

       >>> AME.AMEGetExposedParamVisibilityExpr('custom_exposed_folder_5', 'component_2')
	   >>> 'param2-param1'
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_param_visibility_expr|data_path=%s" % exposed_datapath)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return ret

def AMESetExposedParamLocation(exposed_datapath, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a exposed parameter in the active circuit.

       AMESetExposedParamLocation(string, string, int, string)

       First string argument is the name of the exposed parameter.

       Second string argument is ID of the parent GP group under which this exposed parameter
       is to be added. If None is passed, the exposed parameter will be added to top level.

       Third integer argument is position of this exposed parameter in its parent/root.
       If None is passed, the exposed parameter will be appended at last.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedParamLocation('mass_gp', 'gp_folder_5', 1, 'component_2')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_location", exposed_datapath + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedParamLocation(exposed_datapath, sc_alias_path = None):
    """Gets the location of a exposed parameter group in the active circuit.

       (string, int) = AMEGetExposedParamLocation(string, string)

       First string argument is the name of the exposed parameter.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the location of the given exposed parameter.

       >>> AME.AMEGetExposedParamLocation('k@component_3', 'component_3')
       >>> ('custom_exposed_4', 7)
       >>> AME.AMEGetExposedParamLocation('constant@component_2', 'component_2')
       >>> ('[TOP LEVEL EXPOSED PARAM]', 2)
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_param_location|data_path=%s" \
       % exposed_datapath))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetExposedParamGroupLocation(group_id, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a exposed parameter group in the active circuit.

       AMESetExposedParamGroupLocation(string, string, int, string)

       First string argument is the ID of the GP group.

       Second string argument is ID of the parent group in which this GP group
       is to be added. If None is passed, the exposed group will be added to top level.

       Third integer argument is position of this exposed group in its parent/root.
       If None is passed, the exposed group will be appended at last under its parent.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedParamGroupLocation('custom_exposed_folder_2', None, 3, 'component_3')
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_group_location", group_id + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedParamGroupLocation(group_id, sc_alias_path = None):
    """Gets the location of an exposed parameter group in the active circuit.

       (string, int) = AMEGetExposedParamGroupLocation(string, string)

       First string argument is the ID of the exposed parameter group.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the location of the given exposed parameter group.

       >>> AME.AMEGetExposedParamGroupLocation('custom_exposed_folder_1', 'component_1')
       >>> ('[TOP LEVEL EXPOSED GROUP]', 7)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)

    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_param_group_location|group_id=%s" % group_id))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetExposedParamGroupName(group_id, new_name, sc_alias_path = None):
    """Sets the name of a exposed parameter group in the active circuit.

       AMESetExposedParamGroupName(string, string, string)

       First string argument is the ID of the exposed parameter group.

       Second string argument is new name to be assigned to the exposed parameter group.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedParamGroupName('custom_exposed_folder_5', 'new_folder_name', 'component_2')
    """
    if (new_name is None or len(new_name) == 0):
       raise AccessError(INVALID_EXPOSED_GROUP_NAME)
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_param_group_name", group_id + ','+ new_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedParamGroupsList(sc_alias_path = None):
    """Gets the list of all exposed parameter groups in the active circuit.

       [(string, string), (string, string), ..., (string, string)] = AMEGetExposedParamGroupsList(string)

       First string argument is alias path of the supercomponent from which the list
       of exposed parameter groups will be obtained. If ignored, active supercomponent circuit will be considered.

       Returns a list of tuple of group ID and group name of all the
       exposed parameter groups in the given circuit

       >>> AME.AMEGetExposedParamGroupsList('component_3')
       >>> [('custom_exposed_folder_1', 'foldler_name_1'), ('custom_exposed_folder_2', 'foldler_name_2'), \
           ('custom_exposed_folder_3', 'foldler_name_3')]
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_param_groups_list")
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    tuple_list = _TupleListFromXML(tree)
    return (tuple_list)

# Exposed variable APIs

def AMECreateExposedVarFromDataPath(data_path, exposed_name = None, exposed_title = None, \
    parent_group_id = None, position = None, sc_alias_path = None):
    """Creates an exposed variable from submodel variable in the active circuit.

       string = AMECreateExposedVarFromDataPath(string, string, string, string, int, string)

       First string argument is the data path of the submodel variable.

       Second string argument is the exposed name of the exposed variable.
       If ignored, default exposed name will be set.

       Third string argument is the exposed title of the exposed variable.
       If ignored, default exposed title will be set.

       Fourth string argument is ID of the parent group in which this exposed variable
       is to be added. If ignored, the exposed variable will be added to top level.

       Fifth integer argument is position of this exposed variable in its parent/root.
       If ignored, the exposed variable will be appended at last.

       Sixth string argument is alias path of the supercomponent in which we are going to
       expose variable. If ignored, active supercomponent circuit will be considered.

       Returns the datapath of the newly created exposed variable.

       >>> AME.AMECreateExposedVarFromDataPath('force@component', 'exposed_name', 'exposed_title', \
       'custom_exposed_folder_2', 1, 'component_2')
       'force@component_1'
    """
    if(data_path is None or len(data_path) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if exposed_name is None:
       exposed_name = str("")
    if exposed_title is None:
       exposed_title = str("")
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_var_from_data_path", data_path + ','+ \
          exposed_name + ',' + exposed_title + ',' + parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMECreateExposedVarGroup(group_name = None, parent_group_id = None, position = None, sc_alias_path = None):
    """Creates a exposed variable group in the active circuit.

       string = AMECreateExposedVarGroup(string, string, int, string)

       First string argument is the name of the exposed variable group.
       If ignored, a default name will be set to the group.

       Second string argument is ID of the parent group in which this exposed variable group
       is to be added. If ignored, the exposed variable group will be added to top level.

       Third integer argument is position of this exposed variable group in its parent/root.
       If ignored, the exposed variable group will be appended at last.

       Fourth string argument is alias path of the supercomponent in which we are going to create the
       expose variable group. If ignored, active supercomponent circuit will be considered.

       Returns the ID of the newly created exposed variable group.

       >>> AME.AMECreateExposedVarPGroup('mechanical_folder', 'custom_exposed_folder_3', 4, 'component_3')
       'custom_exposed_folder_5'
    """
    if group_name is None:
       group_name = str("")
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=create_exposed_var_group", group_name + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise
    return (ret)

def AMEDeleteExposedVar(exposed_datapath, sc_alias_path = None):
    """Deletes a exposed variable from the active circuit.

       AMEDeleteExposedVar(string, string)

       First string argument is the datapath of the exposed variable.

       Second string argument is alias path of the supercomponent from which we are going to
       delete expose variable. If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEDeleteExposedVar('pressure@component_2', 'component_2')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_exposed_var", exposed_datapath)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEDeleteExposedVarGroup(group_id, sc_alias_path = None):
    """Deletes a exposed variable group from the active circuit.

       AMEDeleteExposedVarGroup(string, string)

       First string argument is the Id of the exposed variable group.

       Second string argument is alias path of the supercomponent from which we are going to
       delete expose variable group. If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEDeleteExposedVarGroup('custom_exposed_folder', 'component_2')
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=delete_exposed_var_group", group_id)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMESetExposedVarName(exposed_datapath, new_exposed_name, sc_alias_path = None):
    """Sets the name of a exposed variable in the active circuit. Returns
	   the new datapath of the exposed variable.

       string = AMESetExposedVarName(string, string, string)

       First string argument is the datapath of the exposed variable.

       Second string argument is the new exposed name to be set.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

	   Returns the new datapath of the exposed variable

       >>> AME.AMESetExposedVarName('velocity@component_2', 'new_name', 'component_1')
	   >>> 'new_name@component_2'
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if (new_exposed_name is None or len(new_exposed_name) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_var_name", exposed_datapath + ','+ new_exposed_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

    return ret

def AMEGetExposedVarsList(sc_alias_path = None):
    """Gets the list of all exposed variables in the active circuit.

       [string, string, string, ... , string] = AMEGetExposedVarsList(string)

       First string argument is alias path of the supercomponent from which the list
       of exposed variables will be obtained. If ignored, active supercomponent circuit will be considered.

       Returns a list of data path and exposed name of all the exposed variables in the given circuit.

       >>> AME.AMEGetExposedVarsList(None)
       >>> [('resistance@component_1', 'resistance'), ('capacitance@component_1', 'capacitance'),
	   ('inductance@component_1', 'inductance')]
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_vars_list")
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    tuple_list = _TupleListFromXML(tree)
    return (tuple_list)

def AMESetExposedVarTitle(exposed_datapath, new_exposed_title, sc_alias_path = None):
    """Sets the title of an exposed variable in the active circuit.

       AMESetExposedVarTitle(string, string, string)

       First string argument is the datapath of the exposed variable.

       Second string argument is the new exposed title to be set.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedVarTitle('stiffmode@component_1', 'new_title', 'component_1')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if (new_exposed_title is None or len(new_exposed_title) == 0):
       raise AccessError(INVALID_EXPOSED_TITLE)
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_var_title", exposed_datapath + ','+ new_exposed_title)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedVarTitle(exposed_datapath, sc_alias_path = None):
    """Sets the title of an exposed variable in the active circuit.

       string = AMEGetExposedVarTitle(string, string)

       First string argument is the datapath of the exposed variable.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMEGetExposedVarTitle('F0@component_2', 'component_2')
       >>> 'index of array'
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_var_title|data_path=%s" % exposed_datapath)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

    return ret

def AMESetExposedVarLocation(exposed_datapath, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a exposed variable in the active circuit.

       AMESetExposedVarLocation(string, string, int, string)

       First string argument is the name of the exposed variable.

       Second string argument is ID of the parent GP group under which this exposed variable
       is to be added. If None is passed, the exposed variable will be added to top level.

       Third integer argument is position of this exposed variable in its parent/root.
       If None is passed, the exposed variable will be appended at last.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedVarLocation('mass_gp', 'custom_exposed_folder_4', 1, 'component_2')
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_var_location", exposed_datapath + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedVarLocation(exposed_datapath, sc_alias_path = None):
    """Gets the location of a exposed variable in the active circuit.

       (string, int) = AMEGetExposedVarLocation(string, string)

       First string argument is the name of the exposed variable.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the location of the given exposed variable.

       >>> AME.AMEGetExposedVarLocation('k@component_3', 'component_1')
       >>> ('custom_exposed_4', 7)
    """
    if (exposed_datapath is None or len(exposed_datapath) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_var_location|data_path=%s" % exposed_datapath))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetExposedVarGroupLocation(group_id, parent_group_id = None, position = None, sc_alias_path = None):
    """Sets the location of a exposed variable group in the active circuit.

       AMESetExposedVarGroupLocation(string, string, int, string)

       First string argument is the ID of the GP group.

       Second string argument is ID of the parent group in which this exposed variable group
       is to be added. If None is passed, the exposed variable group will be added to top level.

       Third integer argument is position of this exposed variable group in its parent/root.
       If None is passed, the exposed variable group will be appended at last under its parent.

       Fourth string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedVarGroupLocation('custom_exposed_folder_2', None, 3, 'component_2')
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(COMMON_ERROR_CODES[0])
    if(position is not None and position < 0):
       raise AccessError(COMMON_ERROR_CODES[2])
    if parent_group_id is None:
       parent_group_id = str("")
    if position is None:
       position = str("")
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_var_group_location", group_id + ','+ \
          parent_group_id + ',' + str(position))
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedVarGroupLocation(group_id, sc_alias_path = None):
    """Gets the location of an exposed variable group in the active circuit.

       (string, int) = AMEGetExposedVarGroupLocation(string, string)

       First string argument is the ID of the exposed variable group.

       Second string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       Returns the location of the given exposed variable group.

       >>> AME.AMEGetExposedVarGroupLocation('custom_exposed_folder_1', None)
       >>> ('[TOP LEVEL EXPOSED GROUP]', 7)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = ET.XML(afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_var_group_location|group_id=%s" % group_id))
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    parent_group_id = str(tree.findtext("parent-group-id"))
    row_number = int(tree.findtext("row-number"))
    return (parent_group_id, row_number)

def AMESetExposedVarGroupName(group_id, new_name, sc_alias_path = None):
    """Sets the name of a exposed variable group in the active circuit.

       AMESetExposedVarGroupName(string, string, string)

       First string argument is the ID of the exposed variable group.

       Second string argument is new name to be assigned to the exposed variable group.

       Third string argument is alias path of the supercomponent which is to  be used.
       If ignored, active supercomponent circuit will be considered.

       >>> AME.AMESetExposedVarGroupName('custom_exposed_folder_5', 'new_folder_name', None)
    """
    if (group_id is None or len(group_id) == 0):
       raise AccessError(EXPOSED_PARAM_VAR_ERROR_CODES[2])
    if (new_name is None or len(new_name) == 0):
       raise AccessError(INVALID_EXPOSED_GROUP_NAME)
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       ret = afp.set(circuit_name + ":" + sc_alias_path + ":cmd=set_exposed_var_group_name", group_id + ','+ new_name)
       raiseGlobalOrExposedParamErrorIfAny(ret)
    except:
        raise

def AMEGetExposedVarGroupsList(sc_alias_path = None):
    """Gets the list of all exposed variable groups in the active circuit.

       [(string, string), (string, string), ..., (string, string)] = AMEGetExposedVarGroupsList(string)

       First string argument is alias path of the supercomponent from which the list
       of exposed variable groups will be obtained. If ignored, active supercomponent circuit will be considered.

       Returns a list of tuple of group ID and group name of all the
       exposed variable groups in the given circuit

       >>> AME.AMEGetExposedVarGroupsList(None)
       >>> [('custom_exposed_folder_1', 'foldler_name_1'), ('custom_exposed_folder_2', 'foldler_name_2'), \
           ('custom_exposed_folder_3', 'foldler_name_3')]
    """
    if sc_alias_path is None:
       sc_alias_path = str("")

    circuit_name = _get_circuit(None)
    _ensure_mode(circuit_name, PARAMETER_MODE)
    try:
       tree = afp.get(circuit_name + ":" + sc_alias_path + ":cmd=get_exposed_var_groups_list")
       raiseGlobalOrExposedParamErrorIfAny(tree)
    except:
        raise

    tuple_list = _TupleListFromXML(tree)
    return (tuple_list)


def AMEAddProperty(alias_path, property_type, property_name, property_value = "", circuit = None):
    """
       Adds the property to the given alias path.  If alias path is empty, property will be
       added to current circuit

       AMEAddProperty(string, string, string, string, circuit)

       First string argument is alias path of the component or line to add property.
       Second string argument is type of the property to be added.
       Allowed property types are: "number", "text", "formatted-text", "date", "file-link",
       "file-attached", "image", "enum"
       Third string argument is name of the property
       Fourth string argument is value of the property. This is the optional one.
       If not given default value will be set.
       Fifth argument is the circuit

       Returns
       - Id of the property. Ex: id5.

       >>> AME.AMEAddProperty(comp_tank_right, "text", "Message", "Good Luck" )
       >>> Output: id5
    """
    if not alias_path:
       property_target = _get_circuit(circuit)
    else:
       property_target = make_elem_property_id(*(_parse_aliaspath(alias_path)))

    value = _StringListToXML([str(property_type), str(property_name), str(property_value)])
    ret_value = afp.set(property_target+":cmd=add_property", value)
    return (ret_value)


def AMERemoveProperty(property_id , circuit = None):
    """
       Removes the given property id from the circuit

       AMERemoveProperty(string, circuit)

       First string argument is the property_id.
       Second argument is the circuit

       >>> AME.AMERemoveProperty(prop_id)
    """
    circuit = _get_circuit(circuit)
    value = _StringListToXML([str(property_id)])
    ret_value = afp.set(circuit+":cmd=remove_property", value)
    return (ret_value)

def AMESetPropertyValue(property_id , property_value, circuit = None):
    """
       Sets the new given value to the property. This property will
       be used to set single value for properties. This cannot be used
       for enumeration properties.

       AMESetPropertyValue(string, string, circuit)

       First string argument is the property_id.
       Second string argument is the property value
       Third argument is circuit

       >>> AME.AMESetPropertyValue(prop_id, "789")
    """
    circuit = _get_circuit(circuit)
    value = _StringListToXML([str(property_id), str(property_value)])
    ret_value = afp.set(circuit+":cmd=set_property_value", value)
    return (ret_value)

def AMESetPropertyValues(property_id , property_values, circuit = None):
    """
       Sets the new given values to the enumeration property

       AMESetPropertyValues(string, list, circuit)

       First string argument is the property_id.
       Second list argument is the property values
       Third argument is circuit

       >>> AME.AMESetPropertyValue(prop_id, ["789", "89", "100"])
    """
    circuit = _get_circuit(circuit)
    property_values.insert(0, str(property_id))
    value = _StringListToXML(property_values)
    ret_value = afp.set(circuit+":cmd=set_property_values", value)
    return (ret_value)

def AMEGetPropertyValue(property_id, circuit = None):
    """
       Returns the value of the given property

       AMEGetPropertyValue(string, circuit)

       First string argument is the property_id.
       Returns property value as the string

       >>> AME.AMEGetPropertyValue(prop_id)
       >>> Output: 789
    """
    circuit = _get_circuit(circuit)
    ret_value = afp.get(circuit+":cmd=get_property_value&" + str(property_id))
    return (ret_value)

def AMEGetPropertyValues(property_id, circuit = None):
    """
       Returns the values of the enumeration property

       AMEGetPropertyValue(list, circuit)

       First string argument is the property_id.
       Returns the list of possible enumeration property values

       >>> AME.AMEGetPropertyValues(prop_id)
       >>> Output: "789", "89", "100"
    """
    circuit = _get_circuit(circuit)
    ret_value = afp.get(circuit+":cmd=get_property_values&" + str(property_id))
    return _StringListFromXML(ret_value)


def AMESetPropertyName(property_id , property_name, circuit = None):
    """
       Sets new name to the property

       AMESetPropertyName(string, string, circuit)

       First string argument is the property_id.
       Second string argument is the new property name
       Third argument is circuit

       >>> AME.AMESetPropertyName(prop_id, "new_name")
    """
    circuit = _get_circuit(circuit)
    value = _StringListToXML([str(property_id), str(property_name)])
    ret_value = afp.set(circuit+":cmd=set_property_name", value)
    return (ret_value)

def AMEGetPropertyName(property_id, circuit = None):
    """
       Returns the name of the property

       AMEGetPropertyName(string, circuit)

       First string argument is the property_id.
       Returns the name of the property as string

       >>> AME.AMEGetPropertyName(prop_id)
       >>> Output: new_name
    """
    circuit = _get_circuit(circuit)
    ret_value = afp.get(circuit+":cmd=get_property_name&" + str(property_id))
    return (ret_value)

def AMESetPropertyType(property_id , property_type, property_value, circuit = None):
    """
       Sets new type to the property

       AMESetPropertyType(string, string, string, circuit)

       First string argument is the property_id.
       Second string argument is the new property type
       Allowed property types are: "number", "text", "formatted-text", "date", "file-link",
       "file-attached", "image", "enum"
       Third string argument is the property value
       Fourth argument is circuit

       >>> AME.AMESetPropertyType(prop_id, "text", "text_value_for_type_change")
    """
    circuit = _get_circuit(circuit)
    value = _StringListToXML([str(property_id), str(property_type), str(property_value)])
    ret_value = afp.set(circuit+":cmd=set_property_type", value)
    return (ret_value)

def AMEGetPropertyType(property_id, circuit = None):
    """
       Returns the type of the property

       AMEGetPropertyType(string, circuit)

       First string argument is the property_id.
       Returns the type of the property as string

       >>> AME.AMEGetPropertyType(prop_id)
       >>> Output: text
    """
    circuit = _get_circuit(circuit)
    ret_value = afp.get(circuit+":cmd=get_property_type&" + str(property_id))
    return (ret_value)


def AMEGetPropertyTarget(property_id, circuit = None):
    """
       Returns the target of the property

       AMEGetPropertyTarget(string, circuit)

       First string argument is the property_id.
       Returns the target of the property

       >>> AME.AMEGetPropertyTarget(prop_id)
       >>> Output: aliaspath:mass1port
    """
    circuit = _get_circuit(circuit)
    ret_value = afp.get(circuit+":cmd=get_property_target&" + str(property_id))
    return (ret_value)

def AMEGetPropertyList(alias_path = ""):
    """
       Returns the list of the properties in the circuit.

       AMEGetPropertyList(alias_path)

       First argument is alias_path. If alias_path is empty the
       properties will be returned for current circuit
       Returns the list of properties

       >>> AME.AMEGetPropertyList("spring01")
       >>> Output: id5, id6
       >>> AME.AMEGetPropertyList("")
       >>> Output: id0, id1, id2, id3, id4, id5, id6
    """
    property_target = make_elem_property_id(*(_parse_aliaspath(alias_path)))
    ret_value = afp.get(property_target+":cmd=property_list")
    return _StringListFromXML(ret_value)

def AMECreateCircuit():
    """
       Creates a new circuit.

       string = AMECreateCircuit()

       Returns the created circuit identifier.

       [WARNING] This function is for testing purposes only. Use at your own risk.

       >>> AME.AMECreateCircuit()
       >>> Output: unnamed_system(1)
    """
    return afp.set("cmd=create_circuit", "")


def AMESetElementAlias(alias, new_alias, circuit=None):
    """
       Change the element alias to new name.
       AMESetElementAlias("fofx", "fofx_new")
       >>> AME.AMESetElementAlias("fofx", "fofx_new")
    """
    return _AME.AMESetElementAlias(**locals())

def AMEEditDynamicComponent(alias_path, dyn_param, circuit = None):
    return _AME.AMEEditDynamicComponent(**locals())

def AMEIsTunableParameter(data_path):
    return _AME.AMEIsTunableParameter(**locals())

def AMEGetLinkedVariable(data_path):
    return _AME.AMEGetLinkedVariable(**locals())

def AMEGetCompParVarList(data_path, circuit = None):
    return _AME.AMEGetCompParVarList(**locals())

LA_FREE_STATE = "free state"
LA_FIXED_STATE = "fixed state"
LA_STATE_OBSERVER = "state observer"
LA_CLEAR = "clear"
LA_CONTROL = "control"
LA_OBSERVER = "observer"

################################################################################
#   \brief Sets the LA Status value to the  given variable data path
#   \version 2019-03-05 VMS CORE-16854: created
################################################################################
def AMESetLA(data_path, value, circuit=None):
    """
        Sets the LA Status value of variable.

        AMESetLA(string, string)

        First string argument is the data path of variable.

        Second string argument is LA Status value which is tobe set

        Fourth string argument is circuit

        >>> AME.AMESetLA('x1@rubber', LA_OBSERVER)
        >>> AME.AMESetLA('x1@rubber', LA_FIXED_STATE)
    """
    _ensure_mode_at_least(_AME._ensure_circuit(circuit), PARAMETER_MODE)
    return _AME.AMESetLAStatus(**locals())

################################################################################
#   \brief Returns the submodel-name.
#   \version 2019-04-24 SSW CORE-18317: Created
################################################################################
def AMEGetCompSubmodelName(alias_path):
    """Returns the Submodel Name.

        string = AMEGetCompSubmodelName(string)

        First argument is a string representing the alias path of the element (component or line)
        to test.

        >>> AME.AMEGetCompSubmodelName('myicon')
        MAS001 (submodel-name)
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return afp.get(alias_propid + ':comp_subname')

################################################################################
#   \brief Returns if the submodel needs update check.
#   \version 2019-04-24 SSW CORE-18317: Created
################################################################################
def AMECompEmbeddedSubmodelNeedsUpdateCheck(alias_path):
    """Returns the Submodel Name.

        bool = AMECompEmbeddedSubmodelNeedsUpdateCheck(string)

        First argument is a string representing the alias path of the element (component or line)
        to test.

        >>> AME.AMECompEmbeddedSubmodelNeedsUpdateCheck('myicon')
        False (or True)
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return bool(int(afp.get(alias_propid + ':prop=embedded_submodel_needs_update_check')))

################################################################################
#   \brief
#   \version 2019-04-24 SSW CORE-18317: Created
################################################################################
def AMECompEmbeddedSubmodelToUpgrade(alias_path):
    """Returns the Submodel Name.

        bool = AMECompEmbeddedSubmodelToUpgrade(string)

        First argument is a string representing the alias path of the element (component or line)
        to test.

        >>> AME.AMECompEmbeddedSubmodelToUpgrade('myicon')
        False (or True)
    """
    alias_propid = make_elem_property_id(*_parse_aliaspath(alias_path))
    return bool(int(afp.get(alias_propid + ':prop=embedded_submodel_to_upgrade')))

################################################################################
#   \brief Command to set/unset a variable to be saved in the result file
#   \version 2019-07-23 ATv CORE-19684: Created
################################################################################
def AMESaveVariable(variable_path, save_next, circuit=None):
    """Returns the Submodel Name.

        bool = AMESaveVariable(string, boolean)

        First argument is a string representing the variable path, the second is a boolean indicating
        to save or not the variable's value

        >>> AME.AMESaveVariable('v2@mass_friction2port', False)
        False (or True)
    """
    var_name, elem_path, circuit_name = _parse_datapath(variable_path)
    datapath = _make_datapath(var_name, elem_path, circuit_name)

    _ensure_mode_at_least(_AME._ensure_circuit(circuit), PARAMETER_MODE)
    return bool(int(_AME.AMESaveVariable(datapath, save_next)))

################################################################################
#   \brief Check if a variable is to be saved or not in the result file
#   \version 2019-07-23 ATv CORE-19684: Created
################################################################################
def AMEIsSavedVariable(variable_path, circuit=None):
    """Returns the Submodel Name.

        bool = AMEIsSavedVariable(string)

        First argument is a string representing the variable path

        >>> AME.AMEIsSavedVariable('v2@mass_friction2port')
        False (or True)
    """
    var_name, elem_path, circuit_name = _parse_datapath(variable_path)
    datapath = _make_datapath(var_name, elem_path, circuit_name)

    _ensure_mode_at_least(_AME._ensure_circuit(circuit), PARAMETER_MODE)
    return bool(int(_AME.AMEIsSavedVariable(datapath)))

################################################################################
#   \brief Returns the current commercial version name
#   \version 2019-07-15 ATv CORE-18317: Created
################################################################################
def AMEGetCommercialVersionName():
    """Returns the current commercial version name.

        string = AMEGetCommercialVersionName()

        >>> AME.AMEGetCommercialVersionName()
        '2210'
    """
    return _AME.AMEGetCommercialVersionName(**locals())

################################################################################
#   \brief Adds new path(s) to path-list.
#   \version 2019-11-11 SSW CORE-19681: Created
################################################################################
def AMEAddPathsToPathList(paths_to_add):
   """Adds new path(s) to path-list.
      AMEAddPathsToPathList(str_single_path)
      AMEAddPathsToPathList(list_of_paths)
   """
   if isinstance(paths_to_add, basestring):
      paths_to_add = [paths_to_add]

   return _AME.AMEAddPathsToPathList(paths_to_add)

################################################################################
#   \brief Removes path(s) from path-list.
#   \version 2019-11-11 SSW CORE-19681: Created
################################################################################
def AMERemovePathsFromPathList(paths_to_remove):
   """Removes path(s) from path-list.
      AMERemovePathsFromPathList(str_single_path)
      AMERemovePathsFromPathList(list_of_paths)
   """
   if isinstance(paths_to_remove, basestring):
      paths_to_remove = [paths_to_remove]

   return _AME.AMERemovePathsFromPathList(paths_to_remove)

################################################################################
#   \brief Rebuilds category path-list.
#   \version 2019-11-11 SSW CORE-19681: Created
################################################################################
def AMERebuildCategoryPathList():
   """Rebuilds category path-list.
      AMERebuildCategoryPathList()
   """
   return _AME.AMERebuildCategoryPathList(**locals())

################################################################################
#   \brief Returns current path-list.
#   \version 2019-11-11 SSW CORE-19681: Created
################################################################################
def AMEGetPathList():
   """Returns current path-list.
      list = AMEGetPathList()
   """
   return _AME.AMEGetPathList(**locals())

################################################################################
#   \brief Activates in path-list the path(s).
#   \version 2023-04-26 YRl CORE-25247: Created
################################################################################
def AMEActivatePathsInPathList(paths_to_activate):
   """Activates path(s) in path-list given in argument.
      AMEActivatePathsInPathList(str_single_path)
      AMEActivatePathsInPathList(list_of_paths)

      If a path is already active, nothing is done.
      An empty list or a non-existing path in argument results in a error.
   """
   if isinstance(paths_to_activate, basestring):
      paths_to_activate = [paths_to_activate]

   return _AME.AMEActivatePathsInPathList(paths_to_activate)

################################################################################
#   \brief Deactivates in path-list the path(s).
#   \version 2023-04-26 YRl CORE-25247: Created
################################################################################
def AMEDeactivatePathsInPathList(paths_to_deactivate):
   """Deactivates path(s) in path-list given in argument.
      AMEDeactivatePathsInPathList(str_single_path)
      AMEDeactivatePathsInPathList(list_of_paths)

      If a path is already inactive, nothing is done.
      An empty list or a non-existing path in argument results in a error.
      '$AME' cannot be deactivated, it results in an error as well.
   """
   if isinstance(paths_to_deactivate, basestring):
      paths_to_deactivate = [paths_to_deactivate]

   return _AME.AMEDeactivatePathsInPathList(paths_to_deactivate)

################################################################################
#   \brief Returns path-list selected elements.
#   \version 2023-04-24 YRl CORE-25247: Created
################################################################################
def AMEGetActivePathsInPathList():
   """Returns path-list active paths.
      list = AMEGetActivePathsInPathList()
   """
   return _AME.AMEGetActivePathsInPathList(**locals())

################################################################################
#   \brief Returns a list of all available networks in the circuit
#   \version 2019-11-14 GCi CORE-21141: Created
################################################################################
def AMEGetNetworkList(circuit=None):
    """Returns the list of all available networks in the circuit.

        string_list = AMEGetNetworkList()

        >>> AME.AMEGetNetworkList()
        '['SkyNet!NetworkProvider', 'SkyNet!NetworkProvider_1']'
    """
    return _AME.AMEGetNetworkList(**locals())

################################################################################
#   \brief Returns a list of all available network instances in the submodel
#   \version 2019-11-14 GCi CORE-21141: Created
################################################################################
def AMEGetSubmodelNetworkInstanceList(alias_path, circuit=None):
    """Returns the list of all available network instances in the submodel.

        string_list = AMEGetSubmodelNetworkInstanceList(string)

        >>> AME.AMEGetSubmodelNetworkInstanceList('NetworkConsumer')
        '['SkyNet!NetworkProvider', 'SkyNet!NetworkProvider_1']'
    """
    return _AME.AMEGetSubmodelNetworkInstanceList(**locals())
################################################################################
#   \brief Returns the active sketch
#   \version 2019-11-27 ATv CORE-21794: Created
################################################################################
def AMEGetActiveSketch(circuit=None):
    """Returns the active sketch.

       string = AMEGetActiveSketch()

       >>> AME.AMEGetActiveSketch
       project_name(1).component_1
    """
    return _AME.AMEGetActiveSketch(**locals())

################################################################################
#   \brief Returns the port label of specified port index
#   \version 2020-01-06 VMs CORE-22175: Created
################################################################################
def AMEGetSupercomponentPortLabel(port_index,circuit=None):
    """Returns the supercomponent port label.

       string = AMEGetSupercomponentPortLabel(port_index)

       >>> AME.AMEGetSupercomponentPortLabel(1)
       'port_label'
    """
    return _AME.AMEGetSupercomponentPortLabel(**locals())
    return _AME.AMEGetActiveSketch(**locals())

def AMESenseInternalVariables(alias_path, sense_variables, circuit=None):
    """
       Sense the given list of internal variables

       AMESenseInternalVariables(string, list, circuit)

       First string argument is the full alias path of the component to be sensed.
       Second list argument is list of internal varaibles to be sensed
       Third argument is circuit, by default it takes the active circuit name

       >>> AME.AMESenseInternalVariables('springdamper01', ['x', 'kval', 'force', 'damperforce'])
       >>> AME.AMESenseInternalVariables('springdamper01', ['x', 'kval', 'force', 'damperforce'], SC('component_1'))
    """
    if isinstance(sense_variables, basestring):
      sense_variables = [sense_variables]
    return _AME.AMESenseInternalVariables(alias_path, sense_variables, circuit)

def AMEUnSenseInternalVariables(alias_path,  circuit=None):
    """
       UnSenses all the internal variables of the specified component

       AMESenseInternalVariables(string, list, circuit)

       First string argument is the full alias path of the component to be unsensed.
       Second argument is circuit,  by default it takes the active circuit name

       >>> AME.AMEUnSenseInternalVariables('springdamper01')
    """
    return _AME.AMEUnSenseInternalVariables(alias_path, circuit)
def AMEGetSensedInternalVariables(alias_path,  circuit=None):
    '''
       Returns a string_list with all the sensed variables of the given component
          in first argument
       First string argument is the full alias path of the component for which we need the information.
       Second argument is circuit,  by default it takes the active circuit name

       >>> AME.AMEGetSensedInternalVariables('springdamper01')
      ['x', 'kval', 'force', 'damperforce']
    '''
    return _AME.AMEGetSensedInternalVariables(alias_path,  circuit)

def AMEOpenSketchGenerationWizard(file_path=None, applications_path=None, keep_ratio=True, clear_sketch=True, circuit=None):
    '''
       Opens model generation wizard.
       :param file_path: String. Contains path to the system diagram file (.syd ). If defined and valid first wizard page is skipped.
       :param applications_path: String. Custom directory path to application mapping files. If not defined defaults to directory in Amesim installation.
       :param keep_ratio: keeps ratio when generating sketch regarding positions specified in the system diagram file
       :param clear_sketch: clears Amesim sketch before generation
       :param circuit: circuit, by default it takes the active circuit name

       >>> AME.AMEOpenSketchGenerationWizard('C:\data\BalancedVanePump_demo.syd', 'C:\data\CustomApplications', False)
    '''
    return _AME.AMEOpenSketchGenerationWizard(**locals())

def AMEGetBusVariablesUsage(alias_path, port_number):
    """
    Returns for a given bus port:
      - satisfied variables (those used by downstream selector(s) and furnished by the upstream creator)
      - unused variables (those that none of the downstream selector(s) use(s))
      - missing variables missing variables (those that are expected by the downstream selector but not furnished by the upstream creator)
    @param[in] alias_path The full alias path of the component.
    @param[in] port_number The bus port index.
    @return A list of list of strings

    >>> AME.AMEGetBusVariablesUsage('springdamper01', 0)
    [[...], [...], [...]]
    """
    return _AME.AMEGetBusVariablesUsage(**locals())

def AMEGetPortType(alias, port_number):
    """
    Gets the port type corresponding to the port number in the given circuit.

    AMEGetPortType(string, int)

    First string argument is the alias of the component to which the port belongs.

    Second int argument is the port number of the port for which the tag will be fetched.

    >>> AME.AMEGetPortType("dynamic_transmitter", 2)
    lshaft
    """
    elem_path, circuit_name = _parse_aliaspath(alias)
    alias_propid = make_elem_property_id(elem_path, circuit_name)
    ret_value = afp.get(alias_propid + ":get_port_type|" + "port_number=" + urllib.parse.quote(str(port_number)))
    return (ret_value)

def AMEGetSimulationTimeUnit():
   """
    Gets the preferred run time unit (i.e., the start/final time unit)

    >>> AME.AMEGetSimulationTimeUnit()
    min
    """
   return _AME.AMEGetSimulationTimeUnit(**locals())

def AMESetSimulationTimeUnit(unit):
   """
   Sets the preferred run time unit (i.e., the start/final time unit)

   AMESetSimulationTimeUnit(string)

   The argument is the unit to set (e.g., 's', 'min', 'year')

    >>> AME.AMESetSimulationTimeUnit('min')
    """
   return _AME.AMESetSimulationTimeUnit(**locals())

def AMEAddIconAnimation(alias_path, variable_list, operation_list, circuit = None):
   """
      Adds an animation to the given alias path.

      AMEAddIconAnimation(string, list, list, circuit)

      First argument is the alias path of the component for which the animation is to be added.
      Second argument is the list of variables used in animation
      Third argument is the list of operations used in animation
      Fourth argument is the circuit

       >>> var_list = [('x', 'spool_position_varname', 0, 1)]
       >>> opn_list = [('spool_group_svg', 'transform', 'translate(${x} 0)', [('x', 0, 22)])]
       >>> AME.AMEAddIconAnimation('dirvalve_01', var_list, opn_list)
    """

   xml_cmd_arg = str('<ANIM>')

   if variable_list is not None:
      for var_occurence in variable_list:
         xml_cmd_arg += str('<VARIABLE>')
         if (type(var_occurence) is tuple and len(var_occurence)==4):
            xml_cmd_arg += str('<NAME>') + str(var_occurence[0]) + str('</NAME>')
            xml_cmd_arg += str('<VALUE>') + str(var_occurence[1]) + str('</VALUE>')
            xml_cmd_arg += str('<RANGE_MIN>') + str(var_occurence[2]) + str('</RANGE_MIN>')
            xml_cmd_arg += str('<RANGE_MAX>') + str(var_occurence[3]) + str('</RANGE_MAX>')
         else:
            raise TypeError('Unexpected argument: {0}'.format(var_occurence))
         xml_cmd_arg += str('</VARIABLE>')

   if operation_list is not None:
      for op_occurence in operation_list:
         xml_cmd_arg += str('<OPERATION>')
         if (type(op_occurence) is tuple and len(op_occurence)>=3):
            xml_cmd_arg += str('<ID>') + str(op_occurence[0]) + str('</ID>')
            xml_cmd_arg += str('<ATTRIBUTE>') + str(op_occurence[1]) + str('</ATTRIBUTE>')
            xml_cmd_arg += str('<VALUE>') + str(op_occurence[2]) + str('</VALUE>')
            if (len(op_occurence)==4):
               range_list = op_occurence[3]
               for range_occurence in range_list:
                  xml_cmd_arg += str('<RANGE>')
                  xml_cmd_arg += str('<VAR>') + str(range_occurence[0]) + str('</VAR>')
                  xml_cmd_arg += str('<RANGE_MIN>') + str(range_occurence[1]) + str('</RANGE_MIN>')
                  xml_cmd_arg += str('<RANGE_MAX>') + str(range_occurence[2]) + str('</RANGE_MAX>')
                  xml_cmd_arg += str('</RANGE>')
         else:
            raise TypeError('Unexpected argument: {0}'.format(op_occurence))
         xml_cmd_arg += str('</OPERATION>')

   xml_cmd_arg += str('</ANIM>') + '\n'

   circuit_name = _get_circuit(circuit)
   full_path = circuit_name + ':' + alias_path
   ret_value = afp.set(full_path + ":cmd=add_icon_animation", xml_cmd_arg)
