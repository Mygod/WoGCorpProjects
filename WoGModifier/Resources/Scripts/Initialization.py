# This file imports all useful classes to use and defines some functions that it may be shared. It will let it be faster!

import clr
clr.AddReference("System.Xml.Linq")
from System.Xml.Linq import XDocument, XElement
from System.Xml.XPath import Extensions