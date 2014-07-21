doc = XDocument.Parse(input)
root = doc.Element("scene")
edited = False

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatleft"]')
if (element == None) & (root.Attribute("minx") != None) : 
	minx = root.Attribute("minx").Value
	element = XElement("line")
	element.SetAttributeValue("id", "wogcheatleft")
	element.SetAttributeValue("anchor", minx + ",0")
	element.SetAttributeValue("normal", "1,0")
	root.Add(element)
	edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatright"]')
if (element == None) & (root.Attribute("maxx") != None) : 
    maxx = root.Attribute("maxx").Value
    element = XElement("line")
    element.SetAttributeValue("id", "wogcheatright")
    element.SetAttributeValue("anchor", maxx + ",0")
    element.SetAttributeValue("normal", "-1,0")
    root.Add(element)
    edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatground"]')
if (element == None) & (root.Attribute("miny") != None) : 
    miny = root.Attribute("miny").Value
    element = XElement("line")
    element.SetAttributeValue("id", "wogcheatground")
    element.SetAttributeValue("anchor", "0," + miny)
    element.SetAttributeValue("normal", "0,1")
    root.Add(element)
    edited = True

element = Extensions.XPathSelectElement(root, 'line[@id="wogcheatceiling"]')
if (element == None) & (root.Attribute("maxy") != None) : 
    maxy = root.Attribute("maxy").Value
    element = XElement("line")
    element.SetAttributeValue("id", "wogcheatceiling")
    element.SetAttributeValue("anchor", "0," + maxy)
    element.SetAttributeValue("normal", "0,-1")
    root.Add(element)
    edited = True

output = doc
