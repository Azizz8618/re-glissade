program CALIB(output);(*=s7,l3,u+*)
const H=0.1;
type VEC13=array[1..13] of real;
     VEC4=array[1..4] of real;
var X,VX1,VX2,VX3,VK1,VK2,VK3,VK4:VEC13;
    U:VEC4;
    T,TMAX,RSEED,SIGW,DT0,DTSH,TAU,SUME,EGLI,ZERO,VTHR,VHCR,AVY:real;
    KTIP,MODE,ICTRL,NFR,IFLIB,NSTP,NMAX,NEGL,OCE,I:integer;
    QN:real;
    M0,IC0,NF0,IF0:integer;
procedure INITD(var K:integer); fortran;
procedure GLAUTO(var X:VEC13; var U:VEC4); fortran;
procedure TURB; fortran;
procedure PROIZV(var X:VEC13; var U:VEC4; var XD:VEC13); fortran;
procedure GLSET(var T,DT:real; var K,M,IC,NR,IFL:integer;
           var TM:real); fortran;
procedure GLSEED(var RS:real); fortran;
procedure GLBUR(var SIG,TAUIN,WX,WY,WZ:real); fortran;
procedure GLSOST(var VTHO,HCRO:real); fortran;
_( TMAX:=2400.0; RSEED:=7351.0; SIGW:=1.5; DT0:=0.60;
  for KTIP:=1 to 5 do
  begin
    DTSH:=H; TAU:=1.0; ZERO:=0.0;
    M0:=1; IC0:=0; NF0:=999; IF0:=0;
    GLSET(ZERO,DTSH,KTIP,M0,IC0,NF0,IF0,TMAX);
    GLSEED(RSEED);
    GLBUR(SIGW,TAU,ZERO,ZERO,ZERO);
    INITD(KTIP);
    GLSOST(VTHR,VHCR);
    X[1]:=VTHR; X[2]:=0.0; X[3]:=0.0;
    X[4]:=1.0; X[5]:=0.0; X[6]:=0.0; X[7]:=0.0;
    X[8]:=0.0; X[9]:=0.0; X[10]:=0.0;
    X[11]:=-15000.0; X[12]:=0.0; X[13]:=15000.0*0.05241;
    T:=0.0;
    for I:=1 to 3 do U[I]:=0.0;
    U[4]:=DT0;
    SUME:=0.0; NEGL:=0; NSTP:=0;
    NMAX:=trunc(TMAX/DTSH);
    while (X[13]>VHCR) and (NSTP<NMAX) and (X[13]>-100.0) do
    begin
      T:=T+DTSH;
      GLSET(T,DTSH,KTIP,M0,IC0,NF0,IF0,TMAX);
      GLAUTO(X,U);
      TURB;
      PROIZV(X,U,VK1);
      for I:=1 to 13 do VX1[I]:=X[I]+0.5*DTSH*VK1[I];
      PROIZV(VX1,U,VK2);
      for I:=1 to 13 do VX2[I]:=X[I]+0.5*DTSH*VK2[I];
      PROIZV(VX2,U,VK3);
      for I:=1 to 13 do VX3[I]:=X[I]+DTSH*VK3[I];
      PROIZV(VX3,U,VK4);
      for I:=1 to 13 do
        X[I]:=X[I]+DTSH*(VK1[I]+2*VK2[I]+2*VK3[I]+VK4[I])/6.0;
      QN:=sqrt(X[4]*X[4]+X[5]*X[5]+X[6]*X[6]+X[7]*X[7]);
      X[4]:=X[4]/QN; X[5]:=X[5]/QN; X[6]:=X[6]/QN; X[7]:=X[7]/QN;
      EGLI:=X[13]+0.05241*X[11];
      SUME:=SUME+EGLI*EGLI; NEGL:=NEGL+1;
      NSTP:=NSTP+1
    end;
    AVY:=abs(X[2]); OCE:=4;
    if AVY<=4.0 then OCE:=3;
    if AVY<=2.5 then OCE:=2;
    if AVY<=1.5 then OCE:=1;
    writeln('999',KTIP:1,' ',X[2]:8:3,' ',X[11]:8:1,' ',
            X[13]:7:2,' ',NSTP:5,' ',OCE:1)
  end
_).
