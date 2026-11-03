; Project-specific test for ~/cadence_work; not the launcher's generic smoke.
; Read an explicitly named existing project view, without opening it for edit.
let((cv out tech)
  cv=dbOpenCellViewByType("tut_1" "inverter" "schematic" "" "r")
  unless(cv error("Cannot read tut_1/inverter/schematic"))
  tech=techGetTechLibName(ddGetObj("tut_1"))
  out=outfile(strcat(getShellEnvVar("CODEX_VIRTUOSO_RUN") "/cellview.txt"))
  unless(out error("Cannot write readback result"))
  fprintf(out "CELLVIEW %s/%s/%s\n" cv~>libName cv~>cellName cv~>viewName)
  fprintf(out "TECH %L\nINSTANCES %d\nNETS %d\n" tech length(cv~>instances) length(cv~>nets))
  close(out)
  dbClose(cv)
)
