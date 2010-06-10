/*a few helper routines for generating .analyze_frame() decoder methods*/

static PyObject* i_array_to_list(struct i_array *list) {
  PyObject* toreturn;
  PyObject* item;
  ia_size_t i;

  if ((toreturn = PyList_New(0)) == NULL)
    return NULL;
  else {
    for (i = 0; i < list->size; i++) {
      item = PyInt_FromLong(list->data[i]);
      PyList_Append(toreturn,item);
      Py_DECREF(item);
    }
    return toreturn;
  }
}

static PyObject* ia_array_to_list(struct ia_array *list) {
  PyObject *toreturn;
  PyObject *sub_list;
  ia_size_t i;

  if ((toreturn = PyList_New(0)) == NULL)
    return NULL;
  else {
    for (i = 0; i < list->size; i++) {
      sub_list = i_array_to_list(&(list->arrays[i]));
      PyList_Append(toreturn,sub_list);
      Py_DECREF(sub_list);
    }
    return toreturn;
  }
}
