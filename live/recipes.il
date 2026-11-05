; Small, verified IC618 recipes. No connection, process, or target-selection glue.
procedure(cadexInst(name)
  let((matches)
    matches=setof(i cadexCV~>instances i~>name==name)
    unless(length(matches)==1 error("Expected exactly one instance named %s" name))
    car(matches)
  )
)
procedure(cadexInstTerm(name terminal)
  let((terms)
    terms=setof(it cadexInst(name)~>instTerms it~>name==terminal)
    unless(length(terms)==1 error("Expected one terminal %s.%s" name terminal))
    car(terms)
  )
)
procedure(cadexPin(name terminal)
  let((inst terms boxes box)
    inst=cadexInst(name)
    terms=setof(term inst~>master~>terminals term~>name==terminal)
    unless(length(terms)==1 error("Master terminal is missing or ambiguous"))
    foreach(pin car(terms)~>pins
      boxes=cons(dbTransformBBox(pin~>fig~>bBox inst~>transform) boxes)
    )
    unless(length(boxes)==1 error("Pin has multiple physical shapes; inspect geometry explicitly"))
    box=car(boxes)
    list((caar(box)+caadr(box))/2.0 (cadar(box)+cadadr(box))/2.0)
  )
)
procedure(cadexCreate(lib master name origin orient)
  let((symbol inst)
    when(setof(i cadexCV~>instances i~>name==name) error("Instance name already exists: %s" name))
    unless(ddGetObj(lib master "symbol") error("Existing symbol master is missing"))
    symbol=dbFindOpenCellViewByName(lib master "symbol")
    unless(symbol symbol=dbOpenCellViewByType(lib master "symbol" "" "r"))
    unless(symbol error("Cannot open symbol master read-only"))
    inst=dbCreateInst(cadexCV symbol name origin orient)
    unless(inst error("Instance creation failed"))
    inst
  )
)
procedure(cadexParam(name parameter value)
  let((inst cdf param)
    inst=cadexInst(name)
    cdf=cdfGetInstCDF(inst)
    unless(cdf error("Instance has no CDF"))
    ; analogLib/vdc uses vdc, not a database property called dc.
    when(inst~>libName=="analogLib" && inst~>cellName=="vdc" && parameter=="dc"
      parameter="vdc")
    param=cdfFindParamByName(cdf parameter)
    unless(param error("No CDF parameter %s on %s/%s" parameter inst~>libName inst~>cellName))
    if(inst~>libName=="analogLib" && inst~>cellName=="vdc" && parameter=="vdc" && !param~>callback then
      unless(stringp(value) error("analogLib/vdc voltage must be a string value or expression"))
      dbReplaceProp(inst parameter "string" value)
    else
      unless(isCallable('vfoSetParam) error("CDF callback API unavailable; no generic property fallback"))
      vfoSetParam(cdf parameter value)
    )
    cdfFindParamByName(cdfGetInstCDF(inst) parameter)~>value
  )
)
; Move only ownership roots. Native movement carries attached labels with wires.
; The caller explicitly chooses the inspected local neighborhood, not shared nets.
procedure(cadexMoveFigures(figures delta)
  let((unique roots parent covered)
    unless(listp(delta) && length(delta)==2 && numberp(car(delta)) && numberp(cadr(delta))
      error("Move requires a numeric two-coordinate delta"))
    unless(figures error("Move requires an explicit nonempty figure list"))
    foreach(fig figures
      unless(fig && fig~>cellView==cadexCV && member(fig~>objType '("inst" "line" "label" "rect" "path" "polygon"))
        error("Every moved figure must belong to the target cellview"))
      unless(member(fig unique) unique=cons(fig unique))
    )
    foreach(fig unique
      covered=nil parent=fig~>parent
      while(parent
        when(member(parent unique) covered=t)
        parent=parent~>parent
      )
      unless(covered roots=cons(fig roots))
    )
    foreach(fig roots
      unless(dbMoveFig(fig nil list(delta "R0")) error("Move failed; inspect partial state before retrying")))
    length(roots)
  )
)
procedure(cadexWire(points)
  let((wires)
    wires=schCreateWire(cadexCV "draw" "full" points 0.0625 0.0625 0)
    unless(wires error("Wire creation failed; no label will be attached to nil"))
    wires
  )
)
procedure(cadexPinEscape(name terminal distance)
  let((inst other p q dx dy endpoint)
    unless(cadexCV~>viewName=="schematic" && numberp(distance) && distance>0
      error("Pin escape requires a schematic and positive distance"))
    inst=cadexInst(name)
    other=case(terminal ("D" "S") ("S" "D") ("G" "B") ("B" "G") ("PLUS" "MINUS") ("MINUS" "PLUS"))
    unless(other error("No verified opposing pin pair; provide explicit inspected geometry"))
    p=cadexPin(name terminal)
    q=cadexPin(name other)
    dx=car(p)-car(q) dy=cadr(p)-cadr(q)
    unless((abs(dx)<1e-9 && abs(dy)>1e-9) || (abs(dy)<1e-9 && abs(dx)>1e-9)
      error("Opposing pins are not cardinal; inspect geometry rather than guessing"))
    endpoint=if(abs(dx)>1e-9 then list(car(p)+if(dx>0 then distance else -distance) cadr(p))
      else list(car(p) cadr(p)+if(dy>0 then distance else -distance)))
    list(p endpoint)
  )
)
procedure(cadexStub(name terminal netName distance)
  let((points wire label)
    unless(stringp(netName) && strlen(netName)>0 error("A schematic net name is required"))
    points=cadexPinEscape(name terminal distance)
    wire=car(cadexWire(points))
    label=schCreateWireLabel(cadexCV wire cadr(points) netName "lowerLeft" "R0" "stick" .0625 nil)
    unless(label error("Net label creation failed; inspect partial wire before retrying"))
    when(isCallable('cadexExpectNet) && boundp('cadexExpectations)
      cadexExpectNet(name terminal netName))
    points
  )
)
; Bounded replacement for one inspected straight wire. Keep its identity and
; attached labels; preserve each label's fractional anchor along the segment.
procedure(cadexWireSegment(points)
  unless(listp(points) && length(points)==2 error("Expected two segment endpoints"))
  foreach(p points
    unless(listp(p) && length(p)==2 && numberp(car(p)) && numberp(cadr(p))
      error("Wire coordinates must be numeric pairs")))
  unless((caar(points)==caadr(points) && cadar(points)!=cadadr(points)) ||
         (cadar(points)==cadadr(points) && caar(points)!=caadr(points))
    error("Stretch supports one nonzero axis-aligned segment; inspect other routing explicitly"))
  t
)
procedure(cadexStretchWire(points newPoints)
  let((matches wire anchors p q dx dy fraction newAnchor)
    unless(cadexCV~>viewName=="schematic" error("Wire stretch requires a schematic"))
    cadexWireSegment(points) cadexWireSegment(newPoints)
    matches=setof(s cadexCV~>shapes s~>objType=="line" && s~>points==points)
    unless(length(matches)==1 error("Expected exactly one wire with the inspected points"))
    wire=car(matches) p=car(points) q=cadr(points)
    dx=car(q)-car(p) dy=cadr(q)-cadr(p)
    foreach(child wire~>children
      unless(child~>objType=="label" error("Wire has unsupported attached figures; no stretch applied"))
      fraction=if(dx!=0 then (car(child~>xy)-car(p))/dx else (cadr(child~>xy)-cadr(p))/dy)
      unless(fraction>=0 && fraction<=1 &&
        abs(car(child~>xy)-(car(p)+fraction*dx))<1e-9 &&
        abs(cadr(child~>xy)-(cadr(p)+fraction*dy))<1e-9
        error("Attached label anchor is outside the wire; inspect before stretching"))
      newAnchor=list(caar(newPoints)+fraction*(caadr(newPoints)-caar(newPoints))
                     cadar(newPoints)+fraction*(cadadr(newPoints)-cadar(newPoints)))
      anchors=cons(list(child newAnchor) anchors)
    )
    wire~>points=newPoints
    foreach(item anchors car(item)~>xy=cadr(item))
    wire
  )
)
procedure(cadexDeleteWire(points)
  let((matches)
    matches=setof(s cadexCV~>shapes s~>objType=="line" && s~>points==points)
    unless(length(matches)==1 error("Expected exactly one wire with the inspected points"))
    when(car(matches)~>children
      error("Wire owns attached figures; use cadexStretchWire or explicitly preserve them before deletion"))
    dbDeleteObject(car(matches))
  )
)
procedure(cadexDescribe()
  let((instances shapes props pins connections parameters box)
    foreach(inst cadexCV~>instances
      props=nil pins=nil connections=nil parameters=nil
      foreach(prop inst~>prop props=cons(list(prop~>name sprintf(nil "%L" prop~>value)) props))
      foreach(term inst~>master~>terminals
        foreach(pin term~>pins
          box=dbTransformBBox(pin~>fig~>bBox inst~>transform)
          pins=cons(list(term~>name box) pins)
        )
      )
      foreach(it inst~>instTerms
        connections=cons(list(it~>name when(it~>net it~>net~>name)) connections)
      )
      when(cdfGetInstCDF(inst)
        foreach(param cdfGetInstCDF(inst)~>parameters
          parameters=cons(list(param~>name sprintf(nil "%L" param~>type) sprintf(nil "%L" param~>value) sprintf(nil "%L" param~>units)) parameters)
        )
      )
      instances=cons(list(inst~>name inst~>libName inst~>cellName inst~>xy inst~>orient inst~>bBox reverse(props) reverse(pins) reverse(connections) reverse(parameters)) instances)
    )
    foreach(shape cadexCV~>shapes
      shapes=cons(list(shape~>objType shape~>bBox
        if(shape~>objType=="line" then shape~>points else nil)
        if(shape~>objType=="label" then shape~>theLabel else nil)) shapes)
    )
    list(list("target" cadexCV~>libName cadexCV~>cellName cadexCV~>viewName cadexCV~>mode)
      list("modified" dbIsCellViewModified(cadexCV))
      list("checks" envGetVal("schematic" "updateConn") envGetVal("schematic" "runSRC") envGetVal("schematic" "runVIC"))
      list("instances" reverse(instances)) list("shapes" reverse(shapes)))
  )
)
