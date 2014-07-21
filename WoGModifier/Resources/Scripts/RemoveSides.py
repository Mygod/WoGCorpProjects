doc = XDocument.Parse(input)
root = doc.Element("scene")
edited = False

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatleft"]')
if element != None : 
	element.Remove()
	edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatright"]')
if element != None : 
	element.Remove()
	edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatground"]')
if element != None : 
	element.Remove()
	edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatceiling"]')
if element != None : 
	element.Remove()
	edited = True

if edited : output = doc 
else : output = input
