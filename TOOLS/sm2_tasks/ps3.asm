; модель подсистемы 3: сумма двух полей
; Прототип: re-mrv/src/ps/, src/rcd/, src/wcd/
            .ORG    0
START:      LDA     A
            ADA     B
            STA     RES
            HLT
            .ORG    000020
A:          .WORD   22
B:          .WORD   3
RES:        .WORD   0
            .END
