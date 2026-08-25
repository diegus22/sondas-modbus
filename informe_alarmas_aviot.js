const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
        LevelFormat, ShadingType, VerticalAlign, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

const NARANJA = "F39200";
const OSCURO = "1D1D1B";
const GRIS = "666666";
const ROJO = "E53935";
const VERDE = "4CAF50";
const AZUL = "1565C0";

const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: NARANJA, font: "Arial" },
        paragraph: { spacing: { before: 0, after: 120 }, alignment: AlignmentType.LEFT } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: NARANJA, font: "Arial" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: OSCURO, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-1",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-2",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbered-3",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [
          new TextRun({ text: "AVIOT", bold: true, color: NARANJA, size: 18, font: "Arial" }),
          new TextRun({ text: "  |  Informe Tecnico  |  Confidencial", color: GRIS, size: 16, font: "Arial" }),
        ]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: "Ingeniatic Desarrollo S.L.  |  Pagina ", color: GRIS, size: 16 }),
          new TextRun({ children: [PageNumber.CURRENT], color: GRIS, size: 16 }),
          new TextRun({ text: " de ", color: GRIS, size: 16 }),
          new TextRun({ children: [PageNumber.TOTAL_PAGES], color: GRIS, size: 16 }),
        ]
      })] })
    },
    children: [
      // TITULO
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("Informe Tecnico: Problema de Alarmas en Plataforma Aviot")] }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Fecha: 29 de marzo de 2026  |  Autor: Diego Garcia  |  Destinatario: Juanjo", color: GRIS, size: 20 }),
      ]}),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Plataforma: ", color: GRIS, size: 20 }),
        new TextRun({ text: "aviot20.ingeniatic.com", color: AZUL, size: 20 }),
      ]}),
      new Paragraph({ spacing: { after: 200 }, children: [
        new TextRun({ text: "Prioridad: ", size: 20 }),
        new TextRun({ text: "ALTA", bold: true, color: ROJO, size: 20 }),
        new TextRun({ text: " - Las alarmas de inactividad no se estan generando para ningun dispositivo.", size: 20, color: ROJO }),
      ]}),

      // 1. RESUMEN
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Resumen del Problema")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("Se ha detectado que la plataforma Aviot NO genera alarmas cuando una sonda de temperatura/humedad deja de enviar datos. "),
        new TextRun({ text: "Hay sondas caidas desde hace 16 dias sin que se haya generado ninguna notificacion.", bold: true }),
      ]}),
      new Paragraph({ spacing: { after: 200 }, children: [
        new TextRun("El analisis revela que el problema esta en la configuracion de la rule chain "),
        new TextRun({ text: "\"Activity Inactivity Event\"", bold: true, italics: true }),
        new TextRun(", donde dos filtros impiden que se generen alarmas tanto para sondas individuales como para las placas BOARD."),
      ]}),

      // 2. SONDAS AFECTADAS
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. Sondas Afectadas")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("Se han analizado 4 granjas. Las sondas con problemas confirmados son:"),
      ]}),

      // Tabla sondas
      new Table({
        columnWidths: [1800, 2200, 1200, 1200, 1500, 1460],
        rows: [
          new TableRow({
            tableHeader: true,
            children: ["Granja", "Sala", "ID Modbus", "Estado", "Sin datos", "Ultimo valor"].map(h =>
              new TableCell({
                borders: cellBorders,
                width: { size: 1560, type: WidthType.DXA },
                shading: { fill: NARANJA, type: ShadingType.CLEAR },
                verticalAlign: VerticalAlign.CENTER,
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })] })]
              })
            )
          }),
          // Costa Roja ID09
          ...createRow("Costa Roja", "Destete nou Sala 03", "9", "AVERIADA", "16 dias", "27.2C / 72%"),
          // Nova Devesa ID10
          ...createRow("Nova Devesa", "Parideres 12", "10", "AVERIADA", "3 dias", "22.3C / 75%"),
          // Nova Devesa TODAS
          ...createRow("Nova Devesa", "TODAS (25 sondas)", "2-26", "SIN DATOS", "5 horas", "Varios"),
        ]
      }),

      new Paragraph({ spacing: { before: 120, after: 200 }, children: [
        new TextRun({ text: "Nota: ", bold: true }),
        new TextRun("En Nova Devesa, la caida general de las 25 sondas (5h) apunta a un problema de la placa/gateway (Device_D80D80), no de las sondas individuales. La ID 10 (Parideres 12) ya llevaba 3 dias caida antes de la caida general. En Costa Roja la sonda ID 9 lleva 16 dias sin enviar y su ultimo payload fue '255' (error)."),
      ]}),

      // 3. DIAGNOSTICO
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. Diagnostico Tecnico")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Rule Chain: Activity Inactivity Event")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("La rule chain "),
        new TextRun({ text: "\"Activity Inactivity Event\"", bold: true }),
        new TextRun(" (ID: c98b1d60-8a57-11ef-9e81-ef7fcb991fd8) es la encargada de gestionar las alarmas de inactividad. Se han identificado "),
        new TextRun({ text: "dos problemas bloqueantes:", bold: true, color: ROJO }),
      ]}),

      // PROBLEMA 1
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 Problema 1: Filtro excluye sondas individuales")] }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Nodo afectado: ", bold: true }),
        new TextRun("[0] TbJsFilterNode - \"script\""),
      ]}),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Codigo del filtro:", bold: true }),
      ]}),
      new Paragraph({
        spacing: { after: 80 },
        shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
        indent: { left: 360, right: 360 },
        children: [new TextRun({ text: 'if(metadata["deviceType"] === "AvIoT" && metadata["deviceName"].indexOf("_ID") < 0) return true;', font: "Courier New", size: 18, color: ROJO })]
      }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Efecto: ", bold: true }),
        new TextRun("La condicion "),
        new TextRun({ text: 'indexOf("_ID") < 0', font: "Courier New", size: 20 }),
        new TextRun(" hace que SOLO las BOARD (Device_127FB4, Device_D80D80, etc.) pasen el filtro. Todas las sondas individuales (Device_127FB4_"),
        new TextRun({ text: "ID09", bold: true }),
        new TextRun(", Device_D80D80_"),
        new TextRun({ text: "ID10", bold: true }),
        new TextRun(", etc.) se descartan porque su nombre contiene \"_ID\"."),
      ]}),
      new Paragraph({ spacing: { after: 200 }, children: [
        new TextRun({ text: "Consecuencia: ", bold: true, color: ROJO }),
        new TextRun({ text: "Si una sonda individual deja de funcionar, NUNCA se genera alarma. Solo se detectaria la caida de toda la placa BOARD.", color: ROJO }),
      ]}),

      // PROBLEMA 2
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 Problema 2: Atributos de alarma no configurados en las BOARD")] }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Nodo afectado: ", bold: true }),
        new TextRun("[8] TbJsFilterNode - \"alarm enabled?\""),
      ]}),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Codigo del filtro:", bold: true }),
      ]}),
      new Paragraph({
        spacing: { after: 80 },
        shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
        indent: { left: 360, right: 360 },
        children: [new TextRun({ text: 'return (metadata["ss_system"] === "true" && metadata["ss_activity_alarm"] === "true");', font: "Courier New", size: 18, color: ROJO })]
      }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun({ text: "Efecto: ", bold: true }),
        new TextRun("Este filtro exige que la BOARD tenga dos server attributes: "),
        new TextRun({ text: "system = true", font: "Courier New", size: 20, bold: true }),
        new TextRun(" y "),
        new TextRun({ text: "activity_alarm = true", font: "Courier New", size: 20, bold: true }),
        new TextRun(". Se ha verificado que NINGUNA de las 4 BOARD analizadas tiene estos atributos:"),
      ]}),

      // Tabla de atributos
      new Table({
        columnWidths: [2340, 2340, 2340, 2340],
        rows: [
          new TableRow({
            tableHeader: true,
            children: ["BOARD", "system", "activity_alarm", "Alarmas generadas"].map(h =>
              new TableCell({
                borders: cellBorders,
                width: { size: 2340, type: WidthType.DXA },
                shading: { fill: NARANJA, type: ShadingType.CLEAR },
                children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })] })]
              })
            )
          }),
          ...createAttrRow("Device_127FB4 (Costa Roja)", "NO EXISTE", "NO EXISTE", "0"),
          ...createAttrRow("Device_D80D80 (Nova Devesa)", "NO EXISTE", "NO EXISTE", "0"),
          ...createAttrRow("Device_D5B4F8 (Casa Pubill)", "NO EXISTE", "NO EXISTE", "0"),
          ...createAttrRow("Device_2AAA78 (Sopa)", "NO EXISTE", "NO EXISTE", "0"),
        ]
      }),

      new Paragraph({ spacing: { before: 120, after: 200 }, children: [
        new TextRun({ text: "Consecuencia: ", bold: true, color: ROJO }),
        new TextRun({ text: "Aunque la BOARD entre en estado de inactividad y pase el primer filtro, el segundo filtro la descarta porque no tiene los atributos requeridos. Resultado: 0 alarmas generadas en todo el historico del sistema.", color: ROJO }),
      ]}),

      // 3.4 Device Profiles
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.4 Device Profile \"AvIoT\"")] }),
      new Paragraph({ spacing: { after: 200 }, children: [
        new TextRun("Se ha verificado que el device profile "),
        new TextRun({ text: "\"AvIoT\"", bold: true }),
        new TextRun(" (ID: 57688d00-7f9f-11ec-950a-15efba4d84ed), que es el que usan todas las sondas y BOARD, "),
        new TextRun({ text: "no tiene ninguna alarm rule configurada.", bold: true }),
        new TextRun(" Esto no es necesariamente un problema si las alarmas se gestionan desde la rule chain, pero es una capa adicional que podria usarse como respaldo."),
      ]}),

      // PAGINA NUEVA
      new Paragraph({ children: [new PageBreak()] }),

      // 4. FLUJO DE LA RULE CHAIN
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Flujo de la Rule Chain (resumen)")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("El flujo simplificado de la rule chain \"Activity Inactivity Event\" es:"),
      ]}),

      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Message Type Switch ", bold: true }),
        new TextRun("- Detecta eventos Activity, Inactivity y Post Telemetry"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Filtro [0] script ", bold: true }),
        new TextRun({ text: "(BLOQUEANTE)", color: ROJO, bold: true }),
        new TextRun(" - Solo pasa si deviceType=AvIoT Y nombre NO contiene \"_ID\""),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Device to Asset ", bold: true }),
        new TextRun("- Cambia originator del device al asset relacionado"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Filtro [8] alarm enabled? ", bold: true }),
        new TextRun({ text: "(BLOQUEANTE)", color: ROJO, bold: true }),
        new TextRun(" - Exige system=true Y activity_alarm=true"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Create Alarm [17] INACTIVIDAD ", bold: true }),
        new TextRun("- Crea alarma tipo \"ALARMA SIN CONEXION\" (solo en Inactivity Event)"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-1", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Notificacion ", bold: true }),
        new TextRun("- Llama a API REST (Plivo) para enviar SMS/llamada"),
      ]}),
      new Paragraph({ spacing: { before: 120, after: 200 }, children: [
        new TextRun("Los pasos 2 y 4 son los que bloquean la generacion de alarmas actualmente."),
      ]}),

      // 5. SOLUCION PROPUESTA
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Solucion Propuesta")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("Se proponen dos cambios para resolver el problema:"),
      ]}),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 Correccion inmediata: Activar alarmas en las BOARD")] }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun("Anadir los siguientes "),
        new TextRun({ text: "server attributes", bold: true }),
        new TextRun(" a cada BOARD que deba generar alarmas:"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "system = true", font: "Courier New", size: 20 }),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-2", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "activity_alarm = true", font: "Courier New", size: 20 }),
      ]}),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("Esto activaria las alarmas de inactividad para las BOARD (caida de toda la granja). "),
        new TextRun({ text: "No requiere cambios en la rule chain.", bold: true, color: VERDE }),
      ]}),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Correccion completa: Alarmas para sondas individuales")] }),
      new Paragraph({ spacing: { after: 80 }, children: [
        new TextRun("Modificar el filtro del "),
        new TextRun({ text: "nodo [0]", bold: true }),
        new TextRun(" de la rule chain para que tambien procese las sondas individuales. Por ejemplo, cambiar:"),
      ]}),
      new Paragraph({
        spacing: { after: 80 },
        shading: { fill: "FFEBEE", type: ShadingType.CLEAR },
        indent: { left: 360, right: 360 },
        children: [
          new TextRun({ text: "ACTUAL: ", bold: true, size: 18 }),
          new TextRun({ text: 'metadata["deviceName"].indexOf("_ID") < 0', font: "Courier New", size: 18, color: ROJO }),
        ]
      }),
      new Paragraph({
        spacing: { after: 120 },
        shading: { fill: "E8F5E9", type: ShadingType.CLEAR },
        indent: { left: 360, right: 360 },
        children: [
          new TextRun({ text: "PROPUESTO: ", bold: true, size: 18 }),
          new TextRun({ text: 'eliminar esta condicion o crear un flujo paralelo para sondas _ID', font: "Courier New", size: 18, color: VERDE }),
        ]
      }),
      new Paragraph({ spacing: { after: 200 }, children: [
        new TextRun({ text: "Nota importante: ", bold: true }),
        new TextRun("El flujo actual esta disenado para que la alarma se asocie al asset (sala/nave), no al device directamente. Si se incluyen las sondas individuales, habra que asegurarse de que la relacion Device->Asset funcione correctamente para ellas y que no se dupliquen alarmas (una por la sonda y otra por la BOARD)."),
      ]}),

      // 6. VERIFICACION
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Datos de Verificacion")] }),
      new Paragraph({ spacing: { after: 120 }, children: [
        new TextRun("Informacion adicional para la investigacion:"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Rule chain ID: ", bold: true }),
        new TextRun({ text: "c98b1d60-8a57-11ef-9e81-ef7fcb991fd8", font: "Courier New", size: 20 }),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Device Profile AvIoT ID: ", bold: true }),
        new TextRun({ text: "57688d00-7f9f-11ec-950a-15efba4d84ed", font: "Courier New", size: 20 }),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Nodo problematico 1: ", bold: true }),
        new TextRun("[0] TbJsFilterNode \"script\" - filtro _ID"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Nodo problematico 2: ", bold: true }),
        new TextRun("[8] TbJsFilterNode \"alarm enabled?\" - filtro system/activity_alarm"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Nodo de alarma: ", bold: true }),
        new TextRun("[17] TbCreateAlarmNode \"INACTIVIDAD\" - tipo: ALARMA SIN CONEXION"),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 60 }, children: [
        new TextRun({ text: "Total alarmas historicas en todo el sistema: ", bold: true }),
        new TextRun({ text: "0", bold: true, color: ROJO }),
      ]}),
      new Paragraph({ numbering: { reference: "numbered-3", level: 0 }, spacing: { after: 200 }, children: [
        new TextRun({ text: "Sonda mas tiempo caida: ", bold: true }),
        new TextRun("Costa Roja ID09 (Destete nou Sala 03) - 16 dias sin datos"),
      ]}),
    ]
  }]
});

function createRow(granja, sala, id, estado, sinDatos, valor) {
  const estadoColor = estado === "AVERIADA" ? ROJO : NARANJA;
  return [new TableRow({
    children: [
      new TableCell({ borders: cellBorders, width: { size: 1800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: granja, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 2200, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: sala, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 1200, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: id, bold: true, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 1200, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: estado, bold: true, color: estadoColor, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 1500, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: sinDatos, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 1460, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: valor, size: 18 })] })] }),
    ]
  })];
}

function createAttrRow(board, system, alarm, count) {
  return [new TableRow({
    children: [
      new TableCell({ borders: cellBorders, width: { size: 2340, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: board, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 2340, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: system, color: ROJO, bold: true, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 2340, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: alarm, color: ROJO, bold: true, size: 20 })] })] }),
      new TableCell({ borders: cellBorders, width: { size: 2340, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: count, bold: true, size: 20 })] })] }),
    ]
  })];
}

const outputPath = "/Users/certideal/Downloads/Informe_Alarmas_Aviot_ThingsBoard.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log("Informe generado: " + outputPath);
});
