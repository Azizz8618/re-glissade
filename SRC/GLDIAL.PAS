program GLDIAL(input,output,pastel);(*=s7,l3,u+,Y+*)
(************************************************************)
(* ГЛИССАДА-6. ТЕКСТОВЫЙ ДИАЛОГ. ПЕЧАТЬ - ПАСКАЛЬ.             *)
(* ЯДРО - ФОРТРАН: GLINITD, GLPROIZ, GLAUTO, GLNUMR, GLOUT.   *)
(************************************************************)
const H=0.1; RAD=57.2958; NL=41;
type VEC13=array[1..13] of real;
     VEC4=array[1..4] of real;
     Bitset=set of 0..47;
     ARG=record
       buflen,inplen,dummy1,dummy2:integer;
       A:packed array[1..140] of char
     end;
var X,VX1,VX2,VX3,VK1,VK2,VK3,VK4:VEC13;
    U:VEC4; B:ARG; CMD:alfa;
    T,TMAX,RSEED,SIGW,DT0,DTSH,TAU,SUME,EGLI,DTM,ZERO,AVY:real;
    QN,VA,ALF,TH,GA,PS,VTHR,VHCR,ERMAX,ERR:real;
    EPSKM,HNEW,KMHMIN,KMHMAX,KMSF,KMEXP,PFL:real; KMTRY:integer;
    TCTRL,DTCTRL:real; UHOLD:VEC4;
    KTIP,MODE,ICTRL,NFR,IFLIB,NPRN,NMAX,NSTP,NEGL,IPOS:integer;
    I,J,IH,JA,JG,IB,K,OCE:integer; OK,RUN,PAUS:boolean;
    IMODE,IEX,IFLT:integer;
    MANUAL:boolean; DE,DA,DR,DTZ:real;
    RECON:boolean; NFRMX,NEVMX,NSTEP,IEVK:integer;
    RX:VEC13; RU:VEC4; RT:real;
    SCVERT,SCTOCH,SCY,SCSKO,SCUPR,SCPLAV,SCTOT:real; SCZACH:integer;
    SCW1,SCW2,SCW3,SCW4,SCW5,SCW6,SCW7:real;
    SCQ1,SCQ2,SCQ3,SCQ4,SCQ5,SCQ6:real;
    EXKTIP:array[1..5] of integer;
    EXSIGW,EXRSEED,EXDT0,EXTMAX:array[1..5] of real;
    pastel: array[0..25] of Bitset;
(* диалог *)
procedure PASRED(var D:ARG); external;
(* ядро *)
procedure INITD(var K:integer); fortran;
procedure PROIZV(var X:VEC13; var U:VEC4; var XD:VEC13); fortran;
procedure GLAUTO(var X:VEC13; var U:VEC4); fortran;
procedure PROGC(var T:real; var U:VEC4); fortran;
procedure TURB; fortran;
procedure KUTMER(var X:VEC13; var U:VEC4; var DT,ERR:real); fortran;
procedure KUTMAD(var X:VEC13; var U:VEC4; var DT,EPS:real;
           var HNEW,ERR:real; var IFAIL:integer); fortran;
procedure KMRK4(var X:VEC13; var U:VEC4; var H:real); fortran;
procedure KMPAR(var EPS,HMN,HMX,SF:real;
           var NT:integer; var EX:real); fortran;
procedure KMPAR2(var PF:real); fortran;
procedure KMSET(var EPS:real); fortran;
procedure KMSETP(var PF:real); fortran;
procedure GLFINJ(var K:integer; var U:VEC4); fortran;
procedure GLFCLR; fortran;
(* регистратор: параметры в /RECPAR/ *)
procedure RCGPAR(var NF,NE,NS:integer); fortran;
procedure RCSPAR(var NF,NE,NS:integer); fortran;
procedure RECCLR; fortran;
procedure RECPUT(var X:VEC13; var U:VEC4; var T:real); fortran;
procedure RCEVT(var K:integer; var T:real); fortran;
procedure RCN(var NF,NEV:integer); fortran;
procedure RCGET(var J:integer; var X:VEC13; var U:VEC4;
           var T:real); fortran;
procedure RCEGET(var J,K:integer; var T:real); fortran;
(* оценка задания *)
procedure SCCLR; fortran;
procedure SCPUT(var U:VEC4); fortran;
procedure SCCALC(var X:VEC13); fortran;
procedure SCGET(var RV,RT,RY,SS,UP,PP,TT:real; var IS:integer); fortran;
procedure SCWPAR(var WV,WT,WY,WG,WU,WP,PL:real); fortran;
procedure SCQGET(var V1,V2,V3,V4,V5,V6:real); fortran;
procedure PRVIN; fortran;
procedure JUDG(var X:VEC13); fortran;
(* аксессоры GLACC *)
procedure GLSET(var T,DT:real; var K,M,IC,NR,IFL:integer;
           var TM:real); fortran;
procedure GLT(var T:real); fortran;
procedure GLSOST(var VTH,HCR:real); fortran;
procedure GLSEED(var RS:real); fortran;
procedure GLBUR(var SIG,TAU,WX,WY,WZ:real); fortran;
procedure GLSC(var SU:real; var NE:integer); fortran;
procedure GLVOD(var VA,ALF:real); fortran;
procedure GLANG(var X:VEC13; var TH,GA,PS,DTM,EG:real;
           var IP:integer); fortran;
(************************************************************)
procedure GTINT(var N:integer; var OK:boolean);
var P:integer; C:char;
begin
  OK:=true; N:=0; P:=1;
  while (P<=B.INPLEN) and (B.A[P]=' ') do P:=P+1;
  if P>B.INPLEN then begin OK:=false; exit end;
  while P<=B.INPLEN do
  begin
    C:=B.A[P];
    if (C<'0') or (C>'9') then begin OK:=false; exit end;
    N:=N*10+ord(C)-48; P:=P+1
  end
end;
(************************************************************)
procedure GTRL(var R:real; var OK:boolean);
var P,S:integer; F:real; C:char;
begin
  OK:=true; P:=1;
  while (P<=B.INPLEN) and (B.A[P]=' ') do P:=P+1;
  S:=1;
  if P<=B.INPLEN then
    if B.A[P]='-' then begin S:=-1; P:=P+1 end
    else if B.A[P]='+' then P:=P+1;
  R:=0; F:=1;
  while P<=B.INPLEN do
  begin
    C:=B.A[P];
    if C='.' then
    begin
      P:=P+1;
      while P<=B.INPLEN do
      begin
        C:=B.A[P];
        if (C<'0') or (C>'9') then begin OK:=false; exit end;
        R:=R*10+ord(C)-48; F:=F*10; P:=P+1
      end
    end
    else
    begin
      if (C<'0') or (C>'9') then begin OK:=false; exit end;
      R:=R*10+ord(C)-48; P:=P+1
    end
  end;
  R:=S*R/F
end;
(************************************************************)
procedure GTALF(var A:alfa);
var P:integer;
begin
  for P:=1 to 6 do
    if P<=B.INPLEN then A[P]:=B.A[P] else A[P]:=' '
end;
(************************************************************)
procedure ASK;
begin
  writeln;
  write('> ');
  B.BUFLEN:=80; B.INPLEN:=0;
  PASRED(B)
end;
(************************************************************)
procedure PARAMS;
begin
  writeln('GLISSADA-6 / TEKSTOVY DIALOG');
  writeln('TIP 1..5 :'); ASK; GTINT(KTIP,OK);
  writeln('MODE 1 AVTO / 2 PROG :'); ASK; GTINT(MODE,OK);
  writeln('ICTRL 0 BATCH / 1 TERM :'); ASK; GTINT(ICTRL,OK);
  writeln('NFR SEK :'); ASK; GTINT(NFR,OK);
  writeln('IFLIB 0/1 :'); ASK; GTINT(IFLIB,OK);
  writeln('TMAX :'); ASK; GTRL(TMAX,OK);
  writeln('RSEED :'); ASK; GTRL(RSEED,OK);
  writeln('SIGW :'); ASK; GTRL(SIGW,OK);
  writeln('DT0 :'); ASK; GTRL(DT0,OK)
end;
(************************************************************)
procedure INIT;
begin
  KMPAR(EPSKM,KMHMIN,KMHMAX,KMSF,KMTRY,KMEXP);
  KMPAR2(PFL);
  TCTRL:=0.0; DTCTRL:=H;
  GLFCLR;
  RECCLR; SCCLR;
  MANUAL:=false; DE:=0.0; DA:=0.0; DR:=0.0; DTZ:=DT0;
  DTSH:=H; TAU:=1.0; ZERO:=0.0;
  GLSET(ZERO,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
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
  if MODE=2 then PRVIN;
  NPRN:=trunc(NFR/DTSH); if NPRN<1 then NPRN:=999999;
  NMAX:=trunc(TMAX/DTSH)
end;
(************************************************************)
procedure DOSTP;
var I,IFAIL:integer;
begin
  if ICTRL<>3 then
  begin
    T:=T+DTSH;
    GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
    if MANUAL then
    begin
      U[1]:=DE; U[2]:=DA; U[3]:=DR; U[4]:=DTZ
    end
    else if MODE=1 then GLAUTO(X,U) else PROGC(T,U)
  end
  else
  begin
    if T>=TCTRL then
    begin
      if MANUAL then
      begin
        U[1]:=DE; U[2]:=DA; U[3]:=DR; U[4]:=DTZ
      end
      else if MODE=1 then GLAUTO(X,U) else PROGC(T,U);
      for I:=1 to 4 do UHOLD[I]:=U[I];
      TCTRL:=T+DTCTRL
    end
    else for I:=1 to 4 do U[I]:=UHOLD[I]
  end;
  SCPUT(U);
  TURB;
  if ICTRL=3 then
  begin
    KUTMAD(X,U,DTSH,EPSKM,HNEW,ERR,IFAIL);
    DTSH:=HNEW;
    if ERR>ERMAX then ERMAX:=ERR;
    T:=T+DTSH;
    GLSET(T,DTSH,KTIP,MODE,ICTRL,NFR,IFLIB,TMAX);
    KMRK4(X,U,DTSH)
  end
  else
  begin
    if ICTRL>=2 then
    begin
      KUTMER(X,U,DTSH,ERR);
      if ERR>ERMAX then ERMAX:=ERR
    end;
    PROIZV(X,U,VK1);
    for I:=1 to 13 do VX1[I]:=X[I]+0.5*DTSH*VK1[I];
    PROIZV(VX1,U,VK2);
    for I:=1 to 13 do VX2[I]:=X[I]+0.5*DTSH*VK2[I];
    PROIZV(VX2,U,VK3);
    for I:=1 to 13 do VX3[I]:=X[I]+DTSH*VK3[I];
    PROIZV(VX3,U,VK4);
    for I:=1 to 13 do
      X[I]:=X[I]+DTSH*(VK1[I]+2*VK2[I]+2*VK3[I]+VK4[I])/6.0
  end;
  QN:=sqrt(X[4]*X[4]+X[5]*X[5]+X[6]*X[6]+X[7]*X[7]);
  X[4]:=X[4]/QN; X[5]:=X[5]/QN; X[6]:=X[6]/QN; X[7]:=X[7]/QN;
  EGLI:=X[13]+0.05241*X[11];
  SUME:=SUME+EGLI*EGLI; NEGL:=NEGL+1;
  NSTP:=NSTP+1;
  if RECON and (NSTP mod NSTEP=0) then RECPUT(X,U,T)
end;
(************************************************************)
procedure PRFRM;
var I,J,IH,JA,IB:integer; HGL:real;
begin
  GLANG(X,TH,GA,PS,DTM,EGLI,IPOS);
  GLVOD(VA,ALF);
  IB:=21+TRUNC(X[12]/5.0);
  if IB<1 then IB:=1;
  if IB>41 then IB:=41;
  writeln;
  writeln('T=',T:7:1,' TIP=',KTIP:1,' DALN=',DTM:7:0,
          ' VYS=',X[13]:7:1,' Y=',X[12]:7:1);
  writeln(' VYS PROFILE             | PLAN SVERHU');
  JA:=31-TRUNC(DTM/500.0);
  for IH:=8 downto 0 do
  begin
    write(' ',IH*100:4,' |');
    for J:=1 to 30 do
    begin
      HGL:=0.05241*(31-J)*500.0;
      if (IH=TRUNC(X[13]/100.0)) and (J=JA) then write('*')
      else if TRUNC(HGL/100.0)=IH then write('.')
      else if IH=0 then write('=')
      else write(' ')
    end;
    write(' |');
    if IH=8 then
    begin
      write('    |====|');
      for J:=1 to IB do write(' ');
      write('*'); writeln
    end
    else if IH=0 then writeln('    |====|')
    else writeln('    |    |')
  end;
  writeln('     15km  10km  5km  0');
  writeln(' GLISS 3 GR |----*----| EGLI=',EGLI:7:1,' M');
  writeln(' KURS LUCH |----*----| Y=',X[12]:7:1,' M');
  writeln(' SKOR=',VA:6:1,' VERT=',X[2]:6:2,
          ' ATAKA=',ALF:5:1,' TYAG=',100*U[4]:3:0)
end;
(************************************************************)
procedure SCRROW(NM:alfa; V,Q,W:real);
begin
  write(NM,V:10:2,Q:8:2,W:6:2,' ');
  if Q>=0.9 then begin writeln('ОТЛ'); exit end;
  if Q>=0.7 then begin writeln('ХОР'); exit end;
  if Q>=0.4 then begin writeln('УДВ'); exit end;
  writeln('НЕУД')
end;
(************************************************************)
procedure PRTSCR;
begin
  SCGET(SCVERT,SCTOCH,SCY,SCSKO,SCUPR,SCPLAV,SCTOT,SCZACH);
  SCWPAR(SCW1,SCW2,SCW3,SCW4,SCW5,SCW6,SCW7);
  SCQGET(SCQ1,SCQ2,SCQ3,SCQ4,SCQ5,SCQ6);
  writeln('ДЕБРИФИНГ ЗАДАНИЯ');
  writeln('КОМПОНЕНТ   ЗНАЧЕНИЕ КАЧЕСТВО ВЕС СТАТУС');
  SCRROW('ВЕРТ  ',SCVERT,SCQ1,SCW1);
  SCRROW('ТОЧКА ',SCTOCH,SCQ2,SCW2);
  SCRROW('ОТ ОСИ',SCY,SCQ3,SCW3);
  SCRROW('СКО   ',SCSKO,SCQ4,SCW4);
  SCRROW('ПЕРЕУП',SCUPR,SCQ5,SCW5);
  SCRROW('НЕПЛАВ',SCPLAV,SCQ6,SCW6);
  writeln('ИТОГО БАЛЛ=',SCTOT:7:3,' ПОРОГ=',SCW7:5:2,
          ' ЗАЧЕТ=',SCZACH:1)
end;
(************************************************************)
procedure PLYREC;
var J,NF,NEV,KEV:integer; TEV:real;
begin
  RCN(NF,NEV);
  writeln('FRAMES=',NF:1,' EVENTS=',NEV:1,' NSTEP=',NSTEP:1);
  for J:=1 to NF do
  begin
    RCGET(J,RX,RU,RT);
    writeln('TELE',J:4,' T=',RT:9:2);
    writeln('  X=',RX[1]:11:4,RX[2]:11:4,RX[3]:11:4,
            RX[4]:11:5,RX[5]:11:5);
    writeln('     ',RX[6]:11:5,RX[7]:11:5,RX[8]:11:5,
            RX[9]:11:5,RX[10]:11:5);
    writeln('     ',RX[11]:11:2,RX[12]:11:3,RX[13]:11:3);
    writeln('  U=',RU[1]:11:5,RU[2]:11:5,RU[3]:11:5,RU[4]:11:5)
  end;
  for J:=1 to NEV do
  begin
    RCEGET(J,KEV,TEV);
    writeln('EV  ',J:4,' K=',KEV:1,' T=',TEV:9:2)
  end
end;
(************************************************************)
procedure CMDLOOP(var CMD:alfa);
begin
  if IMODE=0 then
  begin
    writeln('PIL: STA STE STO PAR PRN AUTO INS EXIT');
    writeln('MAN: EV+ EV- AI+ AI- RU+ RU- TH+ TH-')
  end
  else
    writeln('INS: SEL/FRZ/UNF/INJ/EPS/REC/RPL/RST/SCR/HLP/PIL');
  ASK; GTALF(CMD)
end;
(************************************************************)
begin
  PASTEL[3]:=[48];
  RCGPAR(NFRMX,NEVMX,NSTEP);
  IMODE:=0; IEX:=1;
  EXKTIP[1]:=3; EXSIGW[1]:=0.0; EXRSEED[1]:=7351.0;
  EXDT0[1]:=0.60; EXTMAX[1]:=2400.0;
  EXKTIP[2]:=1; EXSIGW[2]:=1.5; EXRSEED[2]:=7351.5;
  EXDT0[2]:=0.60; EXTMAX[2]:=2400.0;
  EXKTIP[3]:=2; EXSIGW[3]:=0.5; EXRSEED[3]:=7351.5;
  EXDT0[3]:=0.60; EXTMAX[3]:=2400.0;
  EXKTIP[4]:=4; EXSIGW[4]:=0.0; EXRSEED[4]:=7351.5;
  EXDT0[4]:=0.60; EXTMAX[4]:=2400.0;
  EXKTIP[5]:=5; EXSIGW[5]:=0.3; EXRSEED[5]:=7351.5;
  EXDT0[5]:=0.60; EXTMAX[5]:=2400.0;
  PARAMS;
  INIT;
  PAUS:=true; RUN:=false;
  repeat
    if PAUS then
    begin
      CMDLOOP(CMD);
      select
        CMD='PIL   ': begin IMODE:=0; PAUS:=true end;
        CMD='INS   ': begin IMODE:=1; PAUS:=true end;
        CMD='FRZ   ': begin writeln('FREEZE'); IEVK:=10; RCEVT(IEVK,T);
          RUN:=false; PAUS:=true end;
        CMD='UNF   ': begin writeln('UNFREEZE');
          IEVK:=11; RCEVT(IEVK,T); RUN:=true; PAUS:=false end;
        CMD='SEL   ': begin ASK; GTINT(IEX,OK);
          if (IEX>=1) and (IEX<=5) then
          begin
            KTIP:=EXKTIP[IEX]; SIGW:=EXSIGW[IEX];
            RSEED:=EXRSEED[IEX]; DT0:=EXDT0[IEX];
            TMAX:=EXTMAX[IEX]; INIT;
            writeln('EXERCISE=',IEX:1,' SELECTED')
          end else writeln('NO EXERCISE');
          PAUS:=true end;
        CMD='PFL   ': begin ASK; GTRL(PFL,OK); KMSETP(PFL);
          writeln('PFL=',PFL:10:3) end;
        CMD='EPS   ': begin ASK; GTRL(EPSKM,OK); KMSET(EPSKM);
          writeln('EPS=',EPSKM:10:3) end;
        CMD='HLP   ': if IMODE=0 then
          writeln('PIL: STA STE STO PAR PRN AUTO INS EXIT')
          else
          begin
            writeln('INS: SEL FRZ UNF INJ EPS REC RPL');
            writeln('     RST SCR HLP PIL')
          end;
        CMD='AUTO  ': begin MANUAL:=false; writeln('AUTO PILOT') end;
        CMD='EV+   ': begin MANUAL:=true; DE:=DE+0.05;
          if DE>0.30 then DE:=0.30; writeln('DE=',DE:6:3) end;
        CMD='EV-   ': begin MANUAL:=true; DE:=DE-0.05;
          if DE< -0.30 then DE:=-0.30; writeln('DE=',DE:6:3) end;
        CMD='AI+   ': begin MANUAL:=true; DA:=DA+0.05;
          if DA>0.15 then DA:=0.15; writeln('DA=',DA:6:3) end;
        CMD='AI-   ': begin MANUAL:=true; DA:=DA-0.05;
          if DA< -0.15 then DA:=-0.15; writeln('DA=',DA:6:3) end;
        CMD='RU+   ': begin MANUAL:=true; DR:=DR+0.05;
          if DR>0.20 then DR:=0.20; writeln('DR=',DR:6:3) end;
        CMD='RU-   ': begin MANUAL:=true; DR:=DR-0.05;
          if DR< -0.20 then DR:=-0.20; writeln('DR=',DR:6:3) end;
        CMD='TH+   ': begin MANUAL:=true; DTZ:=DTZ+0.05;
          if DTZ>1.0 then DTZ:=1.0; writeln('DTZ=',DTZ:6:3) end;
        CMD='TH-   ': begin MANUAL:=true; DTZ:=DTZ-0.05;
          if DTZ<0.0 then DTZ:=0.0; writeln('DTZ=',DTZ:6:3) end;
        CMD='INJ   ': begin ASK; GTINT(IFLT,OK); GLFINJ(IFLT,U);
          RCEVT(IFLT,T); writeln('FAULT=',IFLT:1,' INJECTED') end;
        CMD='SCR   ': begin PRTSCR; PAUS:=true end;
        CMD='REC   ': begin RECCLR; RECON:=true;
          writeln('REC ON NSTEP=',NSTEP:1) end;
        CMD='RPL   ': begin RECON:=false; PLYREC end;
        CMD='RST   ': begin RECCLR; RECON:=false;
          writeln('REC CLEAR') end;
        CMD='STA   ': begin RUN:=true; PAUS:=false end;
        CMD='STE   ': begin DOSTP; PRFRM; PAUS:=true end;
        CMD='STO   ': begin RUN:=false; PAUS:=true end;
        CMD='PAR   ': begin PARAMS; INIT; PAUS:=true end;
        CMD='PRN   ': PRFRM;
        CMD='EXIT  ': begin writeln('EXIT'); stop end;
        true: writeln('NEPR. KOMANDA')
      end
    end;
    if RUN then
    begin
      DOSTP;
      if (NSTP mod NPRN)=0 then PRFRM;
      if X[13]<=VHCR then
      begin
        PRFRM; GLSC(SUME,NEGL); SCCALC(X); JUDG(X);
        AVY:=abs(X[2]); OCE:=4;
        if AVY<=4.0 then OCE:=3;
        if AVY<=2.5 then OCE:=2;
        if AVY<=1.5 then OCE:=1;
        writeln('OCENKA= ',OCE:1);
        if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
          if ICTRL=3 then writeln('DTSH=',DTSH:8:4);
        RUN:=false; PAUS:=true
      end;
      if X[13] < -100.0 then
      begin writeln('AVARIA: RAZRUSHENIE'); RUN:=false; PAUS:=true end;
      if NSTP>=NMAX then
      begin writeln('LIMIT VREMENI: T=',T:7:0);
            if ICTRL>=2 then
          writeln('KONTROL ERMAX=',ERMAX:10:4);
          if ICTRL=3 then writeln('DTSH=',DTSH:8:4);
            RUN:=false; PAUS:=true end;
      if (not PAUS) and (NSTP mod NPRN=0) and (ICTRL=1)
      then CMDLOOP(CMD)
    end
  until false
end.
