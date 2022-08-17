# architecture

<!-- https://mermaid-js.github.io/mermaid/#/ -->

```{mermaid}
    classDiagram
        SchemaUtils <|-- UI
        SchemaBase  *--  UI
        SchemaBase  <|--  Protocol
        SchemaBase  <|--  Activity
        SchemaUtils <|-- Message
        SchemaBase  <|--  Item
        Item  *--  ResponseOption
        SchemaUtils <|-- ResponseOption
        SchemaUtils <|-- AdditionalNoteObj
        SchemaUtils <|-- unitOption
        SchemaUtils <|-- Choice
        SchemaUtils <|-- AdditionalProperty
        SchemaUtils <|-- SchemaBase
```
