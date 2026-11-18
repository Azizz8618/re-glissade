; модель подсистемы 4: инкремент номера блока
; Прототип: re-mrv/src/ps/, src/rcd/, src/wcd/
            .ORG    0
START:      LDA     A
            ADA     B
            STA     RES
            HLT
            .ORG    000020
A:          .WORD   33
B:          .WORD   5
RES:        .WORD   0
            .END
