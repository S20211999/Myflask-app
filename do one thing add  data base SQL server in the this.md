<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# do one thing add  data base SQL server in the this app.go webapp  for other apps data  thrugh api request this app will save the data in one centerlize postgresql data base  all the SQL server setup option add inside  admin pannel

Based on your Echo framework webapp project, here's how to add PostgreSQL as a centralized database with API endpoints and admin panel configuration:[^1_1][^1_2]

## Database Layer Implementation

First, add the PostgreSQL dependencies and create a database connection pool:

```go
// database/postgres.go
package database

import (
    "context"
    "fmt"
    "sync"
    "time"
    
    "github.com/jackc/pgx/v5/pgxpool"
)

type DBConfig struct {
    Host     string
    Port     int
    User     string
    Password string
    DBName   string
    MaxConns int32
    MinConns int32
}

var (
    db     *pgxpool.Pool
    dbOnce sync.Once
)

func InitDB(ctx context.Context, config DBConfig) (*pgxpool.Pool, error) {
    var err error
    
    dbOnce.Do(func() {
        connString := fmt.Sprintf(
            "postgres://%s:%s@%s:%d/%s?sslmode=disable",
            config.User, config.Password, config.Host, config.Port, config.DBName,
        )
        
        poolConfig, parseErr := pgxpool.ParseConfig(connString)
        if parseErr != nil {
            err = parseErr
            return
        }
        
        poolConfig.MaxConns = config.MaxConns
        poolConfig.MinConns = config.MinConns
        poolConfig.MaxConnLifetime = time.Hour
        poolConfig.MaxConnIdleTime = 30 * time.Minute
        
        db, err = pgxpool.NewWithConfig(ctx, poolConfig)
        if err != nil {
            return
        }
        
        if err = db.Ping(ctx); err != nil {
            return
        }
    })
    
    return db, err
}

func GetDB() *pgxpool.Pool {
    return db
}
```


## API Data Storage Models

Create models for storing data from other applications:[^1_3]

```go
// models/api_data.go
package models

import "time"

type APIData struct {
    ID          int64     `json:"id"`
    AppName     string    `json:"app_name"`
    DataType    string    `json:"data_type"`
    Payload     string    `json:"payload"` // JSON string
    Timestamp   time.Time `json:"timestamp"`
    SourceIP    string    `json:"source_ip"`
    Status      string    `json:"status"`
}

type DBSettings struct {
    ID          int       `json:"id"`
    Host        string    `json:"host"`
    Port        int       `json:"port"`
    Username    string    `json:"username"`
    Password    string    `json:"password"`
    Database    string    `json:"database"`
    MaxConns    int       `json:"max_conns"`
    MinConns    int       `json:"min_conns"`
    IsActive    bool      `json:"is_active"`
    UpdatedAt   time.Time `json:"updated_at"`
}
```


## Database Repository Layer

```go
// repository/api_data_repo.go
package repository

import (
    "context"
    "yourapp/models"
    "github.com/jackc/pgx/v5/pgxpool"
)

type APIDataRepository struct {
    db *pgxpool.Pool
}

func NewAPIDataRepository(db *pgxpool.Pool) *APIDataRepository {
    return &APIDataRepository{db: db}
}

func (r *APIDataRepository) Create(ctx context.Context, data *models.APIData) error {
    query := `
        INSERT INTO api_data (app_name, data_type, payload, timestamp, source_ip, status)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
    `
    return r.db.QueryRow(ctx, query,
        data.AppName, data.DataType, data.Payload,
        data.Timestamp, data.SourceIP, data.Status,
    ).Scan(&data.ID)
}

func (r *APIDataRepository) GetAll(ctx context.Context) ([]models.APIData, error) {
    query := `SELECT id, app_name, data_type, payload, timestamp, source_ip, status 
              FROM api_data ORDER BY timestamp DESC`
    
    rows, err := r.db.Query(ctx, query)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    var dataList []models.APIData
    for rows.Next() {
        var data models.APIData
        err := rows.Scan(&data.ID, &data.AppName, &data.DataType, 
                        &data.Payload, &data.Timestamp, &data.SourceIP, &data.Status)
        if err != nil {
            return nil, err
        }
        dataList = append(dataList, data)
    }
    
    return dataList, nil
}
```


## API Handlers

```go
// handlers/api_handler.go
package handlers

import (
    "net/http"
    "time"
    "yourapp/models"
    "yourapp/repository"
    
    "github.com/labstack/echo/v4"
)

type APIHandler struct {
    repo *repository.APIDataRepository
}

func NewAPIHandler(repo *repository.APIDataRepository) *APIHandler {
    return &APIHandler{repo: repo}
}

func (h *APIHandler) SaveData(c echo.Context) error {
    var data models.APIData
    
    if err := c.Bind(&data); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid request"})
    }
    
    data.Timestamp = time.Now()
    data.SourceIP = c.RealIP()
    data.Status = "received"
    
    if err := h.repo.Create(c.Request().Context(), &data); err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to save data"})
    }
    
    return c.JSON(http.StatusCreated, data)
}

func (h *APIHandler) GetAllData(c echo.Context) error {
    dataList, err := h.repo.GetAll(c.Request().Context())
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": "Failed to retrieve data"})
    }
    
    return c.JSON(http.StatusOK, dataList)
}
```


## Admin Panel Database Configuration

```go
// handlers/admin_handler.go
package handlers

import (
    "net/http"
    "yourapp/database"
    "yourapp/models"
    
    "github.com/labstack/echo/v4"
)

type AdminHandler struct {
    settingsRepo *repository.SettingsRepository
}

func (h *AdminHandler) GetDBSettings(c echo.Context) error {
    settings, err := h.settingsRepo.GetDBSettings(c.Request().Context())
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
    }
    
    // Mask password
    settings.Password = "******"
    return c.JSON(http.StatusOK, settings)
}

func (h *AdminHandler) UpdateDBSettings(c echo.Context) error {
    var settings models.DBSettings
    
    if err := c.Bind(&settings); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid input"})
    }
    
    // Test connection first
    testConfig := database.DBConfig{
        Host:     settings.Host,
        Port:     settings.Port,
        User:     settings.Username,
        Password: settings.Password,
        DBName:   settings.Database,
        MaxConns: int32(settings.MaxConns),
        MinConns: int32(settings.MinConns),
    }
    
    _, err := database.InitDB(c.Request().Context(), testConfig)
    if err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Connection failed: " + err.Error()})
    }
    
    if err := h.settingsRepo.SaveDBSettings(c.Request().Context(), &settings); err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
    }
    
    return c.JSON(http.StatusOK, map[string]string{"message": "Database settings updated successfully"})
}
```


## Main Application Setup

```go
// main.go
package main

import (
    "context"
    "log"
    "yourapp/database"
    "yourapp/handlers"
    "yourapp/repository"
    
    "github.com/labstack/echo/v4"
    "github.com/labstack/echo/v4/middleware"
)

func main() {
    ctx := context.Background()
    
    // Initialize database
    dbConfig := database.DBConfig{
        Host:     "localhost",
        Port:     5432,
        User:     "postgres",
        Password: "yourpassword",
        DBName:   "centraldb",
        MaxConns: 25,
        MinConns: 5,
    }
    
    db, err := database.InitDB(ctx, dbConfig)
    if err != nil {
        log.Fatal("Failed to connect to database:", err)
    }
    defer db.Close()
    
    // Initialize Echo
    e := echo.New()
    e.Use(middleware.Logger())
    e.Use(middleware.Recover())
    e.Use(middleware.CORS())
    
    // Initialize repositories and handlers
    apiRepo := repository.NewAPIDataRepository(db)
    apiHandler := handlers.NewAPIHandler(apiRepo)
    
    settingsRepo := repository.NewSettingsRepository(db)
    adminHandler := handlers.NewAdminHandler(settingsRepo)
    
    // API routes for data ingestion
    api := e.Group("/api/v1")
    api.POST("/data", apiHandler.SaveData)
    api.GET("/data", apiHandler.GetAllData)
    
    // Admin panel routes
    admin := e.Group("/admin")
    admin.GET("/db-settings", adminHandler.GetDBSettings)
    admin.PUT("/db-settings", adminHandler.UpdateDBSettings)
    admin.POST("/db-test", adminHandler.TestDBConnection)
    
    e.Logger.Fatal(e.Start(":8080"))
}
```


## Database Schema

```sql
CREATE TABLE api_data (
    id BIGSERIAL PRIMARY KEY,
    app_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source_ip VARCHAR(45),
    status VARCHAR(20) DEFAULT 'received',
    INDEX idx_app_name (app_name),
    INDEX idx_timestamp (timestamp)
);

CREATE TABLE db_settings (
    id SERIAL PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 5432,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    database VARCHAR(100) NOT NULL,
    max_conns INTEGER DEFAULT 25,
    min_conns INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

This implementation provides a centralized PostgreSQL database with connection pooling, API endpoints for data ingestion from other apps, and admin panel controls for database configuration.[^1_2][^1_1][^1_3]
<span style="display:none">[^1_10][^1_4][^1_5][^1_6][^1_7][^1_8][^1_9]</span>

<div align="center">⁂</div>

[^1_1]: https://www.kelche.co/blog/go/golang-echo-tutorial/

[^1_2]: https://hexacluster.ai/blog/postgresql/postgresql-client-side-connection-pooling-in-golang-using-pgxpool/

[^1_3]: https://www.genislab.com/exchange/rest/creating-a-golang-api-with-echo-framework-and-postgresql/

[^1_4]: https://www.youtube.com/watch?v=c6ve5vYouFA

[^1_5]: https://www.restapiexample.com/golang-tutorial/creating-golang-api-echo-framework-postgresql/

[^1_6]: https://github.com/go-tutorials/go-echo-sql-tutorial

[^1_7]: https://github.com/GoAdminGroup/go-admin

[^1_8]: https://www.golanglearn.com/golang-tutorials/golang-crud-rest-api-with-echo/

[^1_9]: https://github.com/jackc/pgx/discussions/1989

[^1_10]: http://doc.go-admin.cn/en/quick_start/


---

# no i want meltipule other web app can send  data  to this app getway API endpoints this app will create a table and  save the data in centralized PostgreSQL database   . one app data can share and use by other apps. create a extra  commen table called component

Perfect! I'll create a gateway API where multiple apps can send data, dynamically create tables per app, and include a shared "component" table that all apps can access.[^2_1][^2_2][^2_3]

## Complete Implementation

### 1. Database Models and Structures

```go
// models/models.go
package models

import (
    "database/sql/driver"
    "encoding/json"
    "time"
)

// AppData represents data sent by external apps
type AppData struct {
    AppName   string                 `json:"app_name"`
    TableName string                 `json:"table_name"`
    Data      map[string]interface{} `json:"data"`
    Timestamp time.Time              `json:"timestamp"`
}

// Component - Shared table accessible by all apps
type Component struct {
    ID          int64                  `json:"id"`
    Name        string                 `json:"name"`
    Category    string                 `json:"category"`
    Description string                 `json:"description"`
    Datasheet   string                 `json:"datasheet"`
    Metadata    JSONB                  `json:"metadata"`
    CreatedBy   string                 `json:"created_by"`
    CreatedAt   time.Time              `json:"created_at"`
    UpdatedAt   time.Time              `json:"updated_at"`
}

// JSONB type for PostgreSQL JSONB fields
type JSONB map[string]interface{}

// Value implements driver.Valuer interface
func (j JSONB) Value() (driver.Value, error) {
    return json.Marshal(j)
}

// Scan implements sql.Scanner interface
func (j *JSONB) Scan(value interface{}) error {
    bytes, ok := value.([]byte)
    if !ok {
        return nil
    }
    return json.Unmarshal(bytes, j)
}

// TableSchema represents dynamic table structure
type TableSchema struct {
    AppName    string            `json:"app_name"`
    TableName  string            `json:"table_name"`
    Columns    map[string]string `json:"columns"` // column_name: data_type
    CreatedAt  time.Time         `json:"created_at"`
}
```


### 2. Database Repository with Dynamic Table Creation

```go
// repository/gateway_repo.go
package repository

import (
    "context"
    "fmt"
    "strings"
    "yourapp/models"
    
    "github.com/jackc/pgx/v5"
    "github.com/jackc/pgx/v5/pgxpool"
)

type GatewayRepository struct {
    db *pgxpool.Pool
}

func NewGatewayRepository(db *pgxpool.Pool) *GatewayRepository {
    return &GatewayRepository{db: db}
}

// CreateAppTable dynamically creates a table for an app if it doesn't exist
func (r *GatewayRepository) CreateAppTable(ctx context.Context, appName, tableName string, 
    columns map[string]interface{}) error {
    
    // Sanitize table name: app_name + "_" + table_name
    safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()
    
    // Build column definitions from sample data
    var columnDefs []string
    columnDefs = append(columnDefs, "id BIGSERIAL PRIMARY KEY")
    columnDefs = append(columnDefs, "created_at TIMESTAMP DEFAULT NOW()")
    columnDefs = append(columnDefs, "updated_at TIMESTAMP DEFAULT NOW()")
    
    for colName, colValue := range columns {
        colType := inferColumnType(colValue)
        columnDefs = append(columnDefs, fmt.Sprintf("%s %s", 
            pgx.Identifier{colName}.Sanitize(), colType))
    }
    
    // Create table with dynamic columns
    query := fmt.Sprintf(`
        CREATE TABLE IF NOT EXISTS %s (
            %s
        )
    `, safeTableName, strings.Join(columnDefs, ",\n"))
    
    _, err := r.db.Exec(ctx, query)
    if err != nil {
        return fmt.Errorf("failed to create table: %w", err)
    }
    
    // Create index on created_at
    indexQuery := fmt.Sprintf(`
        CREATE INDEX IF NOT EXISTS idx_%s_created_at ON %s(created_at)
    `, appName+"_"+tableName, safeTableName)
    
    _, err = r.db.Exec(ctx, indexQuery)
    return err
}

// InsertAppData inserts data into app-specific table
func (r *GatewayRepository) InsertAppData(ctx context.Context, appName, tableName string, 
    data map[string]interface{}) error {
    
    safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()
    
    var columns []string
    var placeholders []string
    var values []interface{}
    idx := 1
    
    for key, value := range data {
        columns = append(columns, pgx.Identifier{key}.Sanitize())
        placeholders = append(placeholders, fmt.Sprintf("$%d", idx))
        values = append(values, value)
        idx++
    }
    
    query := fmt.Sprintf(`
        INSERT INTO %s (%s) VALUES (%s)
    `, safeTableName, 
       strings.Join(columns, ", "), 
       strings.Join(placeholders, ", "))
    
    _, err := r.db.Exec(ctx, query, values...)
    return err
}

// GetAppData retrieves data from app-specific table
func (r *GatewayRepository) GetAppData(ctx context.Context, appName, tableName string, 
    limit int) ([]map[string]interface{}, error) {
    
    safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()
    
    query := fmt.Sprintf(`
        SELECT * FROM %s ORDER BY created_at DESC LIMIT $1
    `, safeTableName)
    
    rows, err := r.db.Query(ctx, query, limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    var results []map[string]interface{}
    
    for rows.Next() {
        values, err := rows.Values()
        if err != nil {
            return nil, err
        }
        
        fieldDescriptions := rows.FieldDescriptions()
        rowMap := make(map[string]interface{})
        
        for i, fd := range fieldDescriptions {
            rowMap[string(fd.Name)] = values[i]
        }
        
        results = append(results, rowMap)
    }
    
    return results, nil
}

// Helper function to infer PostgreSQL column type from Go value
func inferColumnType(value interface{}) string {
    switch value.(type) {
    case int, int32, int64:
        return "BIGINT"
    case float32, float64:
        return "DOUBLE PRECISION"
    case bool:
        return "BOOLEAN"
    case map[string]interface{}, []interface{}:
        return "JSONB"
    default:
        return "TEXT"
    }
}

// ListAppTables lists all tables for a specific app
func (r *GatewayRepository) ListAppTables(ctx context.Context, appName string) ([]string, error) {
    query := `
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE $1
    `
    
    rows, err := r.db.Query(ctx, query, appName+"_%")
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    var tables []string
    for rows.Next() {
        var tableName string
        if err := rows.Scan(&tableName); err != nil {
            return nil, err
        }
        tables = append(tables, tableName)
    }
    
    return tables, nil
}
```


### 3. Component Repository (Shared Table)

```go
// repository/component_repo.go
package repository

import (
    "context"
    "yourapp/models"
    
    "github.com/jackc/pgx/v5/pgxpool"
)

type ComponentRepository struct {
    db *pgxpool.Pool
}

func NewComponentRepository(db *pgxpool.Pool) *ComponentRepository {
    return &ComponentRepository{db: db}
}

// CreateComponent adds a new component (accessible by all apps)
func (r *ComponentRepository) CreateComponent(ctx context.Context, comp *models.Component) error {
    query := `
        INSERT INTO components (name, category, description, datasheet, metadata, created_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, created_at, updated_at
    `
    return r.db.QueryRow(ctx, query,
        comp.Name, comp.Category, comp.Description, 
        comp.Datasheet, comp.Metadata, comp.CreatedBy,
    ).Scan(&comp.ID, &comp.CreatedAt, &comp.UpdatedAt)
}

// GetComponents retrieves all components
func (r *ComponentRepository) GetComponents(ctx context.Context, category string) ([]models.Component, error) {
    var query string
    var rows pgx.Rows
    var err error
    
    if category != "" {
        query = `SELECT * FROM components WHERE category = $1 ORDER BY created_at DESC`
        rows, err = r.db.Query(ctx, query, category)
    } else {
        query = `SELECT * FROM components ORDER BY created_at DESC`
        rows, err = r.db.Query(ctx, query)
    }
    
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    var components []models.Component
    for rows.Next() {
        var comp models.Component
        err := rows.Scan(&comp.ID, &comp.Name, &comp.Category, &comp.Description,
            &comp.Datasheet, &comp.Metadata, &comp.CreatedBy, 
            &comp.CreatedAt, &comp.UpdatedAt)
        if err != nil {
            return nil, err
        }
        components = append(components, comp)
    }
    
    return components, nil
}

// SearchComponents searches components by name or category
func (r *ComponentRepository) SearchComponents(ctx context.Context, searchTerm string) ([]models.Component, error) {
    query := `
        SELECT * FROM components 
        WHERE name ILIKE $1 OR category ILIKE $1 OR description ILIKE $1
        ORDER BY created_at DESC
    `
    
    rows, err := r.db.Query(ctx, query, "%"+searchTerm+"%")
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    
    var components []models.Component
    for rows.Next() {
        var comp models.Component
        err := rows.Scan(&comp.ID, &comp.Name, &comp.Category, &comp.Description,
            &comp.Datasheet, &comp.Metadata, &comp.CreatedBy,
            &comp.CreatedAt, &comp.UpdatedAt)
        if err != nil {
            return nil, err
        }
        components = append(components, comp)
    }
    
    return components, nil
}
```


### 4. Gateway API Handlers

```go
// handlers/gateway_handler.go
package handlers

import (
    "net/http"
    "strconv"
    "time"
    "yourapp/models"
    "yourapp/repository"
    
    "github.com/labstack/echo/v4"
)

type GatewayHandler struct {
    gatewayRepo   *repository.GatewayRepository
    componentRepo *repository.ComponentRepository
}

func NewGatewayHandler(gr *repository.GatewayRepository, cr *repository.ComponentRepository) *GatewayHandler {
    return &GatewayHandler{
        gatewayRepo:   gr,
        componentRepo: cr,
    }
}

// IngestData - Main endpoint for apps to send data
func (h *GatewayHandler) IngestData(c echo.Context) error {
    var appData models.AppData
    
    if err := c.Bind(&appData); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": "Invalid request format",
        })
    }
    
    // Validate required fields
    if appData.AppName == "" || appData.TableName == "" || appData.Data == nil {
        return c.JSON(http.StatusBadRequest, map[string]string{
            "error": "app_name, table_name, and data are required",
        })
    }
    
    appData.Timestamp = time.Now()
    ctx := c.Request().Context()
    
    // Create table if not exists
    err := h.gatewayRepo.CreateAppTable(ctx, appData.AppName, appData.TableName, appData.Data)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to create/verify table: " + err.Error(),
        })
    }
    
    // Insert data
    err = h.gatewayRepo.InsertAppData(ctx, appData.AppName, appData.TableName, appData.Data)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to insert data: " + err.Error(),
        })
    }
    
    return c.JSON(http.StatusCreated, map[string]interface{}{
        "message":    "Data saved successfully",
        "app_name":   appData.AppName,
        "table_name": appData.TableName,
        "timestamp":  appData.Timestamp,
    })
}

// GetAppData - Retrieve data from specific app table (cross-app data sharing)
func (h *GatewayHandler) GetAppData(c echo.Context) error {
    appName := c.Param("app_name")
    tableName := c.Param("table_name")
    limitStr := c.QueryParam("limit")
    
    limit := 100
    if limitStr != "" {
        if l, err := strconv.Atoi(limitStr); err == nil {
            limit = l
        }
    }
    
    data, err := h.gatewayRepo.GetAppData(c.Request().Context(), appName, tableName, limit)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to retrieve data: " + err.Error(),
        })
    }
    
    return c.JSON(http.StatusOK, map[string]interface{}{
        "app_name":   appName,
        "table_name": tableName,
        "count":      len(data),
        "data":       data,
    })
}

// ListAppTables - List all tables for an app
func (h *GatewayHandler) ListAppTables(c echo.Context) error {
    appName := c.Param("app_name")
    
    tables, err := h.gatewayRepo.ListAppTables(c.Request().Context(), appName)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to list tables",
        })
    }
    
    return c.JSON(http.StatusOK, map[string]interface{}{
        "app_name": appName,
        "tables":   tables,
    })
}

// Component handlers - Shared across all apps
func (h *GatewayHandler) CreateComponent(c echo.Context) error {
    var comp models.Component
    
    if err := c.Bind(&comp); err != nil {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid input"})
    }
    
    // Set created_by from request header or param
    comp.CreatedBy = c.Request().Header.Get("X-App-Name")
    
    err := h.componentRepo.CreateComponent(c.Request().Context(), &comp)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{
            "error": "Failed to create component: " + err.Error(),
        })
    }
    
    return c.JSON(http.StatusCreated, comp)
}

func (h *GatewayHandler) GetComponents(c echo.Context) error {
    category := c.QueryParam("category")
    
    components, err := h.componentRepo.GetComponents(c.Request().Context(), category)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
    }
    
    return c.JSON(http.StatusOK, components)
}

func (h *GatewayHandler) SearchComponents(c echo.Context) error {
    searchTerm := c.QueryParam("q")
    
    if searchTerm == "" {
        return c.JSON(http.StatusBadRequest, map[string]string{"error": "Search term required"})
    }
    
    components, err := h.componentRepo.SearchComponents(c.Request().Context(), searchTerm)
    if err != nil {
        return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
    }
    
    return c.JSON(http.StatusOK, components)
}
```


### 5. Main Application with Routes

```go
// main.go
package main

import (
    "context"
    "log"
    "yourapp/database"
    "yourapp/handlers"
    "yourapp/repository"
    
    "github.com/labstack/echo/v4"
    "github.com/labstack/echo/v4/middleware"
)

func main() {
    ctx := context.Background()
    
    // Initialize database
    dbConfig := database.DBConfig{
        Host:     "localhost",
        Port:     5432,
        User:     "postgres",
        Password: "yourpassword",
        DBName:   "gateway_db",
        MaxConns: 25,
        MinConns: 5,
    }
    
    db, err := database.InitDB(ctx, dbConfig)
    if err != nil {
        log.Fatal("Failed to connect to database:", err)
    }
    defer db.Close()
    
    // Initialize repositories
    gatewayRepo := repository.NewGatewayRepository(db)
    componentRepo := repository.NewComponentRepository(db)
    
    // Initialize handlers
    gatewayHandler := handlers.NewGatewayHandler(gatewayRepo, componentRepo)
    
    // Setup Echo
    e := echo.New()
    e.Use(middleware.Logger())
    e.Use(middleware.Recover())
    e.Use(middleware.CORS())
    
    // Gateway API routes
    api := e.Group("/api/v1")
    
    // Data ingestion endpoint (apps send data here)
    api.POST("/ingest", gatewayHandler.IngestData)
    
    // Cross-app data access
    api.GET("/apps/:app_name/tables", gatewayHandler.ListAppTables)
    api.GET("/apps/:app_name/tables/:table_name/data", gatewayHandler.GetAppData)
    
    // Shared component table (accessible by all apps)
    api.POST("/components", gatewayHandler.CreateComponent)
    api.GET("/components", gatewayHandler.GetComponents)
    api.GET("/components/search", gatewayHandler.SearchComponents)
    
    log.Println("Gateway API running on :8080")
    e.Logger.Fatal(e.Start(":8080"))
}
```


### 6. Database Schema

```sql
-- Shared component table (accessible by all apps)
CREATE TABLE components (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    datasheet VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_components_category ON components(category);
CREATE INDEX idx_components_name ON components(name);
CREATE INDEX idx_components_metadata ON components USING GIN(metadata);

-- Table to track all dynamically created tables
CREATE TABLE table_registry (
    id SERIAL PRIMARY KEY,
    app_name VARCHAR(100) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    full_table_name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(app_name, table_name)
);
```


### 7. Example API Usage

**App 1 sends sensor data:**

```bash
curl -X POST http://localhost:8080/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "sensor_app",
    "table_name": "temperature_logs",
    "data": {
      "temperature": 25.5,
      "humidity": 60.2,
      "location": "Room_A",
      "sensor_id": "TEMP001"
    }
  }'
```

**App 2 retrieves App 1's data:**

```bash
curl http://localhost:8080/api/v1/apps/sensor_app/tables/temperature_logs/data?limit=50
```

**Any app adds component to shared table:**

```bash
curl -X POST http://localhost:8080/api/v1/components \
  -H "Content-Type: application/json" \
  -H "X-App-Name: pcb_design_app" \
  -d '{
    "name": "STM32F407",
    "category": "Microcontroller",
    "description": "ARM Cortex-M4 MCU",
    "datasheet": "https://example.com/datasheet.pdf",
    "metadata": {
      "package": "LQFP100",
      "voltage": "3.3V",
      "flash": "512KB"
    }
  }'
```

This implementation creates a centralized gateway where multiple apps dynamically create their own tables, share data across apps, and access a common component library.[^2_2][^2_3][^2_4][^2_1]
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_20][^2_5][^2_6][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://stackoverflow.com/questions/47809287/create-postgresql-table-dynamically-in-golang

[^2_2]: https://www.glukhov.org/post/2025/11/multitenant-database-patterns/

[^2_3]: https://docs.activestate.com/activego/1.8/pkg/github.com/jackc/pgx/

[^2_4]: https://www.alexedwards.net/blog/using-postgresql-jsonb

[^2_5]: https://www.cloudthat.com/resources/blog/dynamic-table-and-column-selection-in-postgresql/

[^2_6]: https://www.postgresql.org/docs/current/sql-createtable.html

[^2_7]: https://supabase.com/blog/postgres-dynamic-table-partitioning

[^2_8]: https://dev.to/githaiga22/go-ing-full-stack-building-dynamic-web-apps-with-go-postgresql-docker-and-http-servers-4d4i

[^2_9]: https://www.moesif.com/blog/api-analytics/api-strategy/API-Management-How-to-Monitor-API-Usage-Across-Multiple-API-Gateways/

[^2_10]: https://www.reddit.com/r/Database/comments/m5qxnc/how_would_i_create_postgres_table_on_the_fly/

[^2_11]: https://dev.to/shiviyer/how-to-build-multi-tenancy-in-postgresql-for-developing-saas-applications-4b6

[^2_12]: https://learn.microsoft.com/en-us/azure/architecture/microservices/design/gateway

[^2_13]: https://stackoverflow.com/questions/70533049/how-to-parametrize-a-dynamic-query-in-go

[^2_14]: https://pkg.go.dev/github.com/jackc/pgx/v5

[^2_15]: https://github.com/jackc/pgx/discussions/1785

[^2_16]: https://news.ycombinator.com/item?id=28462162

[^2_17]: https://github.com/jackc/pgx/issues/1043

[^2_18]: https://stackoverflow.com/questions/73606458/how-to-scan-jsonb-objects-from-postgresql-to-golang-structs

[^2_19]: https://www.reddit.com/r/golang/comments/1muz3bz/dynamic_sql_and_json_fields/

[^2_20]: https://www.architecture-weekly.com/p/postgresql-jsonb-powerful-storage


---

# app.go

Perfect! I'll modify your existing app.go to integrate PostgreSQL directly, add the multi-app data gateway functionality with dynamic table creation, and include the shared component table with admin panel database settings.[^3_1][^3_2][^3_3]

Here's the updated **app.go** with PostgreSQL integration:

```go
package main

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"golang.org/x/crypto/bcrypt"
	"gopkg.in/gomail.v2"
)

// ============================================
// DATABASE CONNECTION
// ============================================
var (
	db     *pgxpool.Pool
	dbOnce sync.Once
	dbMux  sync.RWMutex
)

type DBConfig struct {
	Host     string `json:"host"`
	Port     int    `json:"port"`
	User     string `json:"user"`
	Password string `json:"password"`
	DBName   string `json:"dbname"`
	MaxConns int32  `json:"max_conns"`
	MinConns int32  `json:"min_conns"`
}

// User levels
const (
	LevelEngineer = "engineer"
	LevelManager  = "manager"
	LevelGM       = "gm"
	LevelAdmin    = "admin"
)

// ============================================
// MODELS
// ============================================

type User struct {
	ID           string    `json:"id"`
	Username     string    `json:"username"`
	Email        string    `json:"email"`
	Password     string    `json:"-"`
	PasswordHash string    `json:"-"`
	Level        string    `json:"level"`
	AssignedApps []string  `json:"assigned_apps"`
	CreatedAt    time.Time `json:"created_at"`
}

type App struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	URL         string    `json:"url"`
	Icon        string    `json:"icon"`
	Description string    `json:"description"`
	Password    string    `json:"-"`
	CreatedAt   time.Time `json:"created_at"`
}

type Session struct {
	Token      string    `json:"token"`
	Username   string    `json:"username"`
	ExpiresAt  time.Time `json:"expires_at"`
	RememberMe bool      `json:"remember_me"`
}

// Component - Shared table accessible by all apps
type Component struct {
	ID          int64                  `json:"id"`
	Name        string                 `json:"name"`
	Category    string                 `json:"category"`
	Description string                 `json:"description"`
	Datasheet   string                 `json:"datasheet"`
	Metadata    map[string]interface{} `json:"metadata"`
	CreatedBy   string                 `json:"created_by"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
}

// AppData - Data sent by external apps
type AppData struct {
	AppName   string                 `json:"app_name"`
	TableName string                 `json:"table_name"`
	Data      map[string]interface{} `json:"data"`
	Timestamp time.Time              `json:"timestamp"`
}

type EmailConfig struct {
	SMTPHost string
	SMTPPort int
	From     string
	Password string
}

var emailConfig = EmailConfig{
	SMTPHost: os.Getenv("SMTP_HOST"),
	SMTPPort: 587,
	From:     os.Getenv("SMTP_FROM"),
	Password: os.Getenv("SMTP_PASSWORD"),
}

// ============================================
// DATABASE INITIALIZATION
// ============================================

func initDB(config DBConfig) error {
	var err error

	connString := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=disable",
		config.User, config.Password, config.Host, config.Port, config.DBName,
	)

	poolConfig, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return fmt.Errorf("failed to parse config: %w", err)
	}

	poolConfig.MaxConns = config.MaxConns
	poolConfig.MinConns = config.MinConns
	poolConfig.MaxConnLifetime = time.Hour
	poolConfig.MaxConnIdleTime = 30 * time.Minute

	dbMux.Lock()
	defer dbMux.Unlock()

	if db != nil {
		db.Close()
	}

	db, err = pgxpool.NewWithConfig(context.Background(), poolConfig)
	if err != nil {
		return fmt.Errorf("failed to create pool: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err = db.Ping(ctx); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	// Create tables
	if err := createTables(ctx); err != nil {
		return fmt.Errorf("failed to create tables: %w", err)
	}

	log.Println("✓ PostgreSQL connected successfully")
	return nil
}

func createTables(ctx context.Context) error {
	schema := `
	-- Users table
	CREATE TABLE IF NOT EXISTS users (
		id VARCHAR(50) PRIMARY KEY,
		username VARCHAR(100) UNIQUE NOT NULL,
		email VARCHAR(255) NOT NULL,
		password_hash VARCHAR(255) NOT NULL,
		level VARCHAR(20) NOT NULL,
		assigned_apps TEXT[],
		created_at TIMESTAMP DEFAULT NOW()
	);

	-- Apps table
	CREATE TABLE IF NOT EXISTS apps (
		id VARCHAR(50) PRIMARY KEY,
		name VARCHAR(255) NOT NULL,
		url VARCHAR(500) NOT NULL,
		icon VARCHAR(500),
		description TEXT,
		password_hash VARCHAR(255) NOT NULL,
		created_at TIMESTAMP DEFAULT NOW()
	);

	-- Sessions table
	CREATE TABLE IF NOT EXISTS sessions (
		token VARCHAR(255) PRIMARY KEY,
		username VARCHAR(100) NOT NULL,
		expires_at TIMESTAMP NOT NULL,
		remember_me BOOLEAN DEFAULT FALSE,
		created_at TIMESTAMP DEFAULT NOW()
	);

	-- Components table (shared across all apps)
	CREATE TABLE IF NOT EXISTS components (
		id BIGSERIAL PRIMARY KEY,
		name VARCHAR(255) NOT NULL,
		category VARCHAR(100) NOT NULL,
		description TEXT,
		datasheet VARCHAR(500),
		metadata JSONB DEFAULT '{}',
		created_by VARCHAR(100),
		created_at TIMESTAMP DEFAULT NOW(),
		updated_at TIMESTAMP DEFAULT NOW()
	);

	-- Database settings table
	CREATE TABLE IF NOT EXISTS db_settings (
		id SERIAL PRIMARY KEY,
		host VARCHAR(255) NOT NULL,
		port INTEGER NOT NULL DEFAULT 5432,
		username VARCHAR(100) NOT NULL,
		password VARCHAR(255) NOT NULL,
		dbname VARCHAR(100) NOT NULL,
		max_conns INTEGER DEFAULT 25,
		min_conns INTEGER DEFAULT 5,
		is_active BOOLEAN DEFAULT TRUE,
		updated_at TIMESTAMP DEFAULT NOW()
	);

	-- Table registry (tracks dynamically created tables)
	CREATE TABLE IF NOT EXISTS table_registry (
		id SERIAL PRIMARY KEY,
		app_name VARCHAR(100) NOT NULL,
		table_name VARCHAR(100) NOT NULL,
		full_table_name VARCHAR(200) NOT NULL,
		column_schema JSONB,
		created_at TIMESTAMP DEFAULT NOW(),
		UNIQUE(app_name, table_name)
	);

	-- Indexes
	CREATE INDEX IF NOT EXISTS idx_components_category ON components(category);
	CREATE INDEX IF NOT EXISTS idx_components_name ON components(name);
	CREATE INDEX IF NOT EXISTS idx_components_metadata ON components USING GIN(metadata);
	CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
	CREATE INDEX IF NOT EXISTS idx_table_registry_app ON table_registry(app_name);
	`

	_, err := db.Exec(ctx, schema)
	return err
}

// ============================================
// DATABASE OPERATIONS
// ============================================

// User operations
func saveUser(ctx context.Context, user *User) error {
	query := `
		INSERT INTO users (id, username, email, password_hash, level, assigned_apps, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (username) 
		DO UPDATE SET email = $3, password_hash = $4, level = $5, assigned_apps = $6
	`
	_, err := db.Exec(ctx, query,
		user.ID, user.Username, user.Email, user.PasswordHash,
		user.Level, user.AssignedApps, user.CreatedAt)
	return err
}

func getUser(ctx context.Context, username string) (*User, error) {
	query := `SELECT id, username, email, password_hash, level, assigned_apps, created_at 
	          FROM users WHERE username = $1`

	var user User
	err := db.QueryRow(ctx, query, username).Scan(
		&user.ID, &user.Username, &user.Email, &user.PasswordHash,
		&user.Level, &user.AssignedApps, &user.CreatedAt)

	if err != nil {
		return nil, err
	}
	return &user, nil
}

func listUsers(ctx context.Context) ([]*User, error) {
	query := `SELECT id, username, email, password_hash, level, assigned_apps, created_at FROM users`
	rows, err := db.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []*User
	for rows.Next() {
		var user User
		err := rows.Scan(&user.ID, &user.Username, &user.Email, &user.PasswordHash,
			&user.Level, &user.AssignedApps, &user.CreatedAt)
		if err != nil {
			continue
		}
		users = append(users, &user)
	}
	return users, nil
}

func deleteUser(ctx context.Context, username string) error {
	_, err := db.Exec(ctx, "DELETE FROM users WHERE username = $1", username)
	return err
}

// App operations
func saveApp(ctx context.Context, app *App) error {
	query := `
		INSERT INTO apps (id, name, url, icon, description, password_hash, created_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (id) 
		DO UPDATE SET name = $2, url = $3, icon = $4, description = $5
	`
	_, err := db.Exec(ctx, query,
		app.ID, app.Name, app.URL, app.Icon, app.Description, app.Password, app.CreatedAt)
	return err
}

func getApp(ctx context.Context, id string) (*App, error) {
	query := `SELECT id, name, url, icon, description, password_hash, created_at 
	          FROM apps WHERE id = $1`

	var app App
	err := db.QueryRow(ctx, query, id).Scan(
		&app.ID, &app.Name, &app.URL, &app.Icon,
		&app.Description, &app.Password, &app.CreatedAt)

	if err != nil {
		return nil, err
	}
	return &app, nil
}

func listApps(ctx context.Context) ([]*App, error) {
	query := `SELECT id, name, url, icon, description, password_hash, created_at FROM apps`
	rows, err := db.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var apps []*App
	for rows.Next() {
		var app App
		err := rows.Scan(&app.ID, &app.Name, &app.URL, &app.Icon,
			&app.Description, &app.Password, &app.CreatedAt)
		if err != nil {
			continue
		}
		apps = append(apps, &app)
	}
	return apps, nil
}

func deleteApp(ctx context.Context, id string) error {
	_, err := db.Exec(ctx, "DELETE FROM apps WHERE id = $1", id)
	return err
}

// Session operations
func saveSession(ctx context.Context, session *Session) error {
	query := `INSERT INTO sessions (token, username, expires_at, remember_me) 
	          VALUES ($1, $2, $3, $4)
			  ON CONFLICT (token) DO UPDATE SET expires_at = $3`
	_, err := db.Exec(ctx, query, session.Token, session.Username, session.ExpiresAt, session.RememberMe)
	return err
}

func getSession(r *http.Request) (*Session, error) {
	cookie, err := r.Cookie("session_token")
	if err != nil {
		return nil, err
	}

	ctx := r.Context()
	query := `SELECT token, username, expires_at, remember_me FROM sessions WHERE token = $1`

	var session Session
	err = db.QueryRow(ctx, query, cookie.Value).Scan(
		&session.Token, &session.Username, &session.ExpiresAt, &session.RememberMe)

	if err != nil {
		return nil, fmt.Errorf("invalid or expired session")
	}

	if time.Now().After(session.ExpiresAt) {
		deleteSession(ctx, session.Token)
		return nil, fmt.Errorf("session expired")
	}

	return &session, nil
}

func deleteSession(ctx context.Context, token string) error {
	_, err := db.Exec(ctx, "DELETE FROM sessions WHERE token = $1", token)
	return err
}

// ============================================
// GATEWAY DATA OPERATIONS
// ============================================

func createAppTable(ctx context.Context, appName, tableName string, columns map[string]interface{}) error {
	safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()

	var columnDefs []string
	columnDefs = append(columnDefs, "id BIGSERIAL PRIMARY KEY")
	columnDefs = append(columnDefs, "created_at TIMESTAMP DEFAULT NOW()")
	columnDefs = append(columnDefs, "updated_at TIMESTAMP DEFAULT NOW()")

	columnSchema := make(map[string]string)
	for colName, colValue := range columns {
		colType := inferColumnType(colValue)
		columnDefs = append(columnDefs, fmt.Sprintf("%s %s",
			pgx.Identifier{colName}.Sanitize(), colType))
		columnSchema[colName] = colType
	}

	query := fmt.Sprintf(`
		CREATE TABLE IF NOT EXISTS %s (
			%s
		)
	`, safeTableName, strings.Join(columnDefs, ",\n"))

	_, err := db.Exec(ctx, query)
	if err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	// Register table
	schemaJSON, _ := json.Marshal(columnSchema)
	regQuery := `
		INSERT INTO table_registry (app_name, table_name, full_table_name, column_schema)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (app_name, table_name) DO NOTHING
	`
	_, err = db.Exec(ctx, regQuery, appName, tableName, appName+"_"+tableName, schemaJSON)

	// Create index
	indexQuery := fmt.Sprintf(`
		CREATE INDEX IF NOT EXISTS idx_%s_created_at ON %s(created_at)
	`, appName+"_"+tableName, safeTableName)
	db.Exec(ctx, indexQuery)

	return err
}

func insertAppData(ctx context.Context, appName, tableName string, data map[string]interface{}) error {
	safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()

	var columns []string
	var placeholders []string
	var values []interface{}
	idx := 1

	for key, value := range data {
		columns = append(columns, pgx.Identifier{key}.Sanitize())
		placeholders = append(placeholders, fmt.Sprintf("$%d", idx))
		values = append(values, value)
		idx++
	}

	query := fmt.Sprintf(`
		INSERT INTO %s (%s) VALUES (%s)
	`, safeTableName,
		strings.Join(columns, ", "),
		strings.Join(placeholders, ", "))

	_, err := db.Exec(ctx, query, values...)
	return err
}

func getAppData(ctx context.Context, appName, tableName string, limit int) ([]map[string]interface{}, error) {
	safeTableName := pgx.Identifier{appName + "_" + tableName}.Sanitize()

	query := fmt.Sprintf(`
		SELECT * FROM %s ORDER BY created_at DESC LIMIT $1
	`, safeTableName)

	rows, err := db.Query(ctx, query, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []map[string]interface{}

	for rows.Next() {
		values, err := rows.Values()
		if err != nil {
			return nil, err
		}

		fieldDescriptions := rows.FieldDescriptions()
		rowMap := make(map[string]interface{})

		for i, fd := range fieldDescriptions {
			rowMap[string(fd.Name)] = values[i]
		}

		results = append(results, rowMap)
	}

	return results, nil
}

func listAppTables(ctx context.Context, appName string) ([]string, error) {
	query := `SELECT table_name FROM table_registry WHERE app_name = $1`

	rows, err := db.Query(ctx, query, appName)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tables []string
	for rows.Next() {
		var tableName string
		if err := rows.Scan(&tableName); err != nil {
			return nil, err
		}
		tables = append(tables, tableName)
	}

	return tables, nil
}

func inferColumnType(value interface{}) string {
	switch value.(type) {
	case int, int32, int64:
		return "BIGINT"
	case float32, float64:
		return "DOUBLE PRECISION"
	case bool:
		return "BOOLEAN"
	case map[string]interface{}, []interface{}:
		return "JSONB"
	default:
		return "TEXT"
	}
}

// Component operations
func createComponent(ctx context.Context, comp *Component) error {
	query := `
		INSERT INTO components (name, category, description, datasheet, metadata, created_by)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, created_at, updated_at
	`
	metadataJSON, _ := json.Marshal(comp.Metadata)
	return db.QueryRow(ctx, query,
		comp.Name, comp.Category, comp.Description,
		comp.Datasheet, metadataJSON, comp.CreatedBy,
	).Scan(&comp.ID, &comp.CreatedAt, &comp.UpdatedAt)
}

func getComponents(ctx context.Context, category string) ([]Component, error) {
	var query string
	var rows pgx.Rows
	var err error

	if category != "" {
		query = `SELECT id, name, category, description, datasheet, metadata, created_by, created_at, updated_at 
		         FROM components WHERE category = $1 ORDER BY created_at DESC`
		rows, err = db.Query(ctx, query, category)
	} else {
		query = `SELECT id, name, category, description, datasheet, metadata, created_by, created_at, updated_at 
		         FROM components ORDER BY created_at DESC`
		rows, err = db.Query(ctx, query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var components []Component
	for rows.Next() {
		var comp Component
		var metadataJSON []byte

		err := rows.Scan(&comp.ID, &comp.Name, &comp.Category, &comp.Description,
			&comp.Datasheet, &metadataJSON, &comp.CreatedBy,
			&comp.CreatedAt, &comp.UpdatedAt)
		if err != nil {
			continue
		}

		json.Unmarshal(metadataJSON, &comp.Metadata)
		components = append(components, comp)
	}

	return components, nil
}

func searchComponents(ctx context.Context, searchTerm string) ([]Component, error) {
	query := `
		SELECT id, name, category, description, datasheet, metadata, created_by, created_at, updated_at
		FROM components 
		WHERE name ILIKE $1 OR category ILIKE $1 OR description ILIKE $1
		ORDER BY created_at DESC
	`

	rows, err := db.Query(ctx, query, "%"+searchTerm+"%")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var components []Component
	for rows.Next() {
		var comp Component
		var metadataJSON []byte

		err := rows.Scan(&comp.ID, &comp.Name, &comp.Category, &comp.Description,
			&comp.Datasheet, &metadataJSON, &comp.CreatedBy,
			&comp.CreatedAt, &comp.UpdatedAt)
		if err != nil {
			continue
		}

		json.Unmarshal(metadataJSON, &comp.Metadata)
		components = append(components, comp)
	}

	return components, nil
}

// ============================================
// HTTP HANDLERS - GATEWAY API
// ============================================

func handleIngestData(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var appData AppData
	if err := json.NewDecoder(r.Body).Decode(&appData); err != nil {
		http.Error(w, "Invalid request format", http.StatusBadRequest)
		return
	}

	if appData.AppName == "" || appData.TableName == "" || appData.Data == nil {
		http.Error(w, "app_name, table_name, and data are required", http.StatusBadRequest)
		return
	}

	appData.Timestamp = time.Now()
	ctx := r.Context()

	// Create table if not exists
	err := createAppTable(ctx, appData.AppName, appData.TableName, appData.Data)
	if err != nil {
		log.Printf("Failed to create table: %v", err)
		http.Error(w, "Failed to create/verify table", http.StatusInternalServerError)
		return
	}

	// Insert data
	err = insertAppData(ctx, appData.AppName, appData.TableName, appData.Data)
	if err != nil {
		log.Printf("Failed to insert data: %v", err)
		http.Error(w, "Failed to insert data", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"message":    "Data saved successfully",
		"app_name":   appData.AppName,
		"table_name": appData.TableName,
		"timestamp":  appData.Timestamp,
	})
}

func handleGetAppData(w http.ResponseWriter, r *http.Request) {
	// Parse URL: /api/gateway/apps/{app_name}/tables/{table_name}/data
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/gateway/apps/"), "/")
	if len(parts) < 3 {
		http.Error(w, "Invalid path", http.StatusBadRequest)
		return
	}

	appName := parts[^3_0]
	tableName := parts[^3_2]
	limit := 100

	data, err := getAppData(r.Context(), appName, tableName, limit)
	if err != nil {
		http.Error(w, "Failed to retrieve data", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"app_name":   appName,
		"table_name": tableName,
		"count":      len(data),
		"data":       data,
	})
}

func handleListAppTables(w http.ResponseWriter, r *http.Request) {
	// Parse URL: /api/gateway/apps/{app_name}/tables
	appName := strings.TrimPrefix(r.URL.Path, "/api/gateway/apps/")
	appName = strings.TrimSuffix(appName, "/tables")

	tables, err := listAppTables(r.Context(), appName)
	if err != nil {
		http.Error(w, "Failed to list tables", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"app_name": appName,
		"tables":   tables,
	})
}

// Component handlers
func handleCreateComponent(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var comp Component
	if err := json.NewDecoder(r.Body).Decode(&comp); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	comp.CreatedBy = r.Header.Get("X-App-Name")
	if comp.CreatedBy == "" {
		comp.CreatedBy = "system"
	}

	err := createComponent(r.Context(), &comp)
	if err != nil {
		log.Printf("Failed to create component: %v", err)
		http.Error(w, "Failed to create component", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(comp)
}

func handleGetComponents(w http.ResponseWriter, r *http.Request) {
	category := r.URL.Query().Get("category")

	components, err := getComponents(r.Context(), category)
	if err != nil {
		http.Error(w, "Failed to retrieve components", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(components)
}

func handleSearchComponents(w http.ResponseWriter, r *http.Request) {
	searchTerm := r.URL.Query().Get("q")

	if searchTerm == "" {
		http.Error(w, "Search term required", http.StatusBadRequest)
		return
	}

	components, err := searchComponents(r.Context(), searchTerm)
	if err != nil {
		http.Error(w, "Failed to search components", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(components)
}

// ============================================
// HTTP HANDLERS - ADMIN DATABASE SETTINGS
// ============================================

func handleGetDBSettings(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	query := `SELECT host, port, username, dbname, max_conns, min_conns FROM db_settings WHERE is_active = true LIMIT 1`

	var config DBConfig
	err = db.QueryRow(r.Context(), query).Scan(
		&config.Host, &config.Port, &config.User, &config.DBName, &config.MaxConns, &config.MinConns)

	if err == sql.ErrNoRows {
		// Return default config
		config = DBConfig{
			Host:     "localhost",
			Port:     5432,
			User:     "postgres",
			DBName:   "gateway_db",
			MaxConns: 25,
			MinConns: 5,
		}
	}

	config.Password = "******" // Mask password
	json.NewEncoder(w).Encode(config)
}

func handleUpdateDBSettings(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var config DBConfig
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// Test connection first
	testConfig := DBConfig{
		Host:     config.Host,
		Port:     config.Port,
		User:     config.User,
		Password: config.Password,
		DBName:   config.DBName,
		MaxConns: config.MaxConns,
		MinConns: config.MinConns,
	}

	if err := initDB(testConfig); err != nil {
		http.Error(w, "Connection failed: "+err.Error(), http.StatusBadRequest)
		return
	}

	// Save settings
	query := `
		INSERT INTO db_settings (host, port, username, password, dbname, max_conns, min_conns, is_active)
		VALUES ($1, $2, $3, $4, $5, $6, $7, true)
		ON CONFLICT (id) DO UPDATE 
		SET host = $1, port = $2, username = $3, password = $4, dbname = $5, 
		    max_conns = $6, min_conns = $7, updated_at = NOW()
	`

	_, err = db.Exec(r.Context(), query,
		config.Host, config.Port, config.User, config.Password,
		config.DBName, config.MaxConns, config.MinConns)

	if err != nil {
		http.Error(w, "Failed to save settings", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]string{"message": "Database settings updated successfully"})
}

func handleTestDBConnection(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var config DBConfig
	if err := json.NewDecoder(r.Body).Decode(&config); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// Test connection
	connString := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=disable",
		config.User, config.Password, config.Host, config.Port, config.DBName,
	)

	testPool, err := pgxpool.New(r.Context(), connString)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": "Failed to connect: " + err.Error(),
		})
		return
	}
	defer testPool.Close()

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	if err := testPool.Ping(ctx); err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": "Connection failed: " + err.Error(),
		})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Connection successful",
	})
}

// ============================================
// HTTP HANDLERS - AUTHENTICATION
// ============================================

func handleLogin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Username   string `json:"username"`
		Password   string `json:"password"`
		RememberMe bool   `json:"remember_me"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	user, err := getUser(r.Context(), req.Username)
	if err != nil {
		log.Printf("User not found: %v", err)
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}

	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.Password)) != nil {
		log.Println("Password mismatch")
		http.Error(w, "Invalid credentials", http.StatusUnauthorized)
		return
	}

	token := generateToken()
	expiresAt := time.Now().Add(24 * time.Hour)
	if req.RememberMe {
		expiresAt = time.Now().Add(30 * 24 * time.Hour)
	}

	session := &Session{
		Token:      token,
		Username:   req.Username,
		ExpiresAt:  expiresAt,
		RememberMe: req.RememberMe,
	}

	if err := saveSession(r.Context(), session); err != nil {
		http.Error(w, "Failed to create session", http.StatusInternalServerError)
		return
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "session_token",
		Value:    token,
		Expires:  expiresAt,
		HttpOnly: true,
		Path:     "/",
	})

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"user": map[string]interface{}{
			"username": user.Username,
			"level":    user.Level,
			"email":    user.Email,
		},
	})
}

func handleLogout(w http.ResponseWriter, r *http.Request) {
	cookie, err := r.Cookie("session_token")
	if err == nil {
		deleteSession(r.Context(), cookie.Value)
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "session_token",
		Value:    "",
		Expires:  time.Now().Add(-1 * time.Hour),
		HttpOnly: true,
		Path:     "/",
	})

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleForgotPassword(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		Email string `json:"email"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	users, _ := listUsers(r.Context())
	var user *User
	for _, u := range users {
		if u.Email == req.Email {
			user = u
			break
		}
	}

	if user == nil {
		json.NewEncoder(w).Encode(map[string]string{
			"message": "If the email exists, a password reset link has been sent",
		})
		return
	}

	tempPassword := generateToken()[:12]
	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(tempPassword), bcrypt.DefaultCost)
	user.PasswordHash = string(hashedPassword)
	saveUser(r.Context(), user)

	go sendPasswordResetEmail(user.Email, tempPassword)

	json.NewEncoder(w).Encode(map[string]string{
		"message": "If the email exists, a password reset link has been sent",
	})
}

func handleChangePassword(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req struct {
		OldPassword string `json:"old_password"`
		NewPassword string `json:"new_password"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	user, err := getUser(r.Context(), session.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	if bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(req.OldPassword)) != nil {
		http.Error(w, "Invalid old password", http.StatusUnauthorized)
		return
	}

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(req.NewPassword), bcrypt.DefaultCost)
	user.PasswordHash = string(hashedPassword)
	saveUser(r.Context(), user)

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleUserInfo(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	user, err := getUser(r.Context(), session.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	json.NewEncoder(w).Encode(user)
}

func handleUserApps(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	user, err := getUser(r.Context(), session.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	var userApps []*App
	for _, appID := range user.AssignedApps {
		if app, err := getApp(r.Context(), appID); err == nil {
			userApps = append(userApps, app)
		}
	}

	json.NewEncoder(w).Encode(userApps)
}

// ============================================
// HTTP HANDLERS - ADMIN
// ============================================

func handleAdminUsers(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	users, err := listUsers(r.Context())
	if err != nil {
		http.Error(w, "Failed to list users", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(users)
}

func handleCreateUser(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req User
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	req.PasswordHash = string(hashedPassword)
	req.ID = generateToken()[:8]
	req.CreatedAt = time.Now()

	if err := saveUser(r.Context(), &req); err != nil {
		http.Error(w, "Failed to create user", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleUpdateUser(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req User
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	user, err := getUser(r.Context(), req.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	user.Email = req.Email
	user.Level = req.Level
	user.AssignedApps = req.AssignedApps
	saveUser(r.Context(), user)

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleDeleteUser(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	username := r.URL.Query().Get("username")
	if username == "admin" {
		http.Error(w, "Cannot delete admin user", http.StatusBadRequest)
		return
	}

	deleteUser(r.Context(), username)
	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleAdminApps(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	apps, err := listApps(r.Context())
	if err != nil {
		http.Error(w, "Failed to list apps", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(apps)
}

func handleCreateApp(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req App
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	req.ID = generateToken()[:8]
	req.CreatedAt = time.Now()

	apiPassword := generateToken()[:16]
	req.Password = hashPassword(apiPassword)

	if err := saveApp(r.Context(), &req); err != nil {
		http.Error(w, "Failed to create app", http.StatusInternalServerError)
		return
	}

	response := map[string]interface{}{
		"id":           req.ID,
		"name":         req.Name,
		"url":          req.URL,
		"icon":         req.Icon,
		"description":  req.Description,
		"created_at":   req.CreatedAt,
		"api_password": apiPassword,
	}

	json.NewEncoder(w).Encode(response)
}

func handleUpdateApp(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req App
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	app, err := getApp(r.Context(), req.ID)
	if err != nil {
		http.Error(w, "App not found", http.StatusNotFound)
		return
	}

	app.Name = req.Name
	app.URL = req.URL
	app.Icon = req.Icon
	app.Description = req.Description
	saveApp(r.Context(), app)

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleDeleteApp(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	appID := r.URL.Query().Get("id")

	users, _ := listUsers(r.Context())
	for _, user := range users {
		for i, id := range user.AssignedApps {
			if id == appID {
				user.AssignedApps = append(user.AssignedApps[:i], user.AssignedApps[i+1:]...)
				saveUser(r.Context(), user)
				break
			}
		}
	}

	deleteApp(r.Context(), appID)
	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

func handleAssignApp(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil || !isAdmin(r.Context(), session.Username) {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	var req struct {
		Username string `json:"username"`
		AppID    string `json:"app_id"`
		Assign   bool   `json:"assign"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	user, err := getUser(r.Context(), req.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusNotFound)
		return
	}

	if req.Assign {
		found := false
		for _, id := range user.AssignedApps {
			if id == req.AppID {
				found = true
				break
			}
		}
		if !found {
			user.AssignedApps = append(user.AssignedApps, req.AppID)
		}
	} else {
		for i, id := range user.AssignedApps {
			if id == req.AppID {
				user.AssignedApps = append(user.AssignedApps[:i], user.AssignedApps[i+1:]...)
				break
			}
		}
	}

	saveUser(r.Context(), user)
	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

// ============================================
// PROXY HANDLER
// ============================================

func handleProxy(w http.ResponseWriter, r *http.Request) {
	session, err := getSession(r)
	if err != nil {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		return
	}

	pathParts := strings.SplitN(strings.TrimPrefix(r.URL.Path, "/proxy/"), "/", 2)
	if len(pathParts) == 0 || pathParts[^3_0] == "" {
		http.Error(w, "Invalid proxy path", http.StatusBadRequest)
		return
	}

	appID := pathParts[^3_0]
	targetPath := "/"
	if len(pathParts) > 1 {
		targetPath = "/" + pathParts[^3_1]
	}

	app, err := getApp(r.Context(), appID)
	if err != nil {
		log.Printf("App not found: %v", err)
		http.Error(w, "App not found", http.StatusNotFound)
		return
	}

	user, err := getUser(r.Context(), session.Username)
	if err != nil {
		http.Error(w, "User not found", http.StatusUnauthorized)
		return
	}

	hasAccess := false
	for _, id := range user.AssignedApps {
		if id == appID {
			hasAccess = true
			break
		}
	}

	if !hasAccess {
		log.Printf("User %s does not have access to app %s", user.Username, appID)
		http.Error(w, "Access denied", http.StatusForbidden)
		return
	}

	target, err := url.Parse(app.URL)
	if err != nil {
		log.Printf("Invalid app URL: %v", err)
		http.Error(w, "Invalid app URL", http.StatusInternalServerError)
		return
	}

	log.Printf("Proxying: appID=%s target=%s path=%s", appID, target.String(), targetPath)

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = target.Scheme
			req.URL.Host = target.Host
			req.URL.Path = targetPath
			req.URL.RawQuery = r.URL.RawQuery
			req.Host = target.Host

			req.Header.Set("X-Forwarded-Host", r.Header.Get("Host"))
			req.Header.Set("X-Forwarded-Proto", "http")
			req.Header.Set("X-Real-IP", r.RemoteAddr)
			req.Header.Set("X-Forwarded-For", r.RemoteAddr)
		},
		ModifyResponse: func(resp *http.Response) error {
			resp.Header.Del("X-Frame-Options")
			resp.Header.Del("Content-Security-Policy")
			resp.Header.Set("X-Frame-Options", "ALLOWALL")

			if location := resp.Header.Get("Location"); location != "" {
				if strings.HasPrefix(location, "/") {
					resp.Header.Set("Location", "/proxy/"+appID+location)
				}
			}
			return nil
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("Proxy error: %v", err)
			http.Error(w, "Proxy error: "+err.Error(), http.StatusBadGateway)
		},
	}

	proxy.ServeHTTP(w, r)
}

// ============================================
// HELPER FUNCTIONS
// ============================================

func initializeDefaultAdmin(ctx context.Context) {
	log.Println("Checking for default admin user...")

	_, err := getUser(ctx, "admin")
	if err == nil {
		log.Println("✓ Admin user already exists")
		return
	}

	log.Println("Creating default admin user...")

	hashedPassword, _ := bcrypt.GenerateFromPassword([]byte("admin123"), bcrypt.DefaultCost)
	admin := &User{
		ID:           "1",
		Username:     "admin",
		Email:        "admin@example.com",
		PasswordHash: string(hashedPassword),
		Level:        LevelAdmin,
		AssignedApps: []string{},
		CreatedAt:    time.Now(),
	}

	if err := saveUser(ctx, admin); err != nil {
		log.Printf("⚠️  WARNING: Could not create default admin: %v", err)
		return
	}

	log.Println("✓ Default admin user created")
	log.Println("  Username: admin")
	log.Println("  Password: admin123")
}

func isAdmin(ctx context.Context, username string) bool {
	user, err := getUser(ctx, username)
	return err == nil && user.Level == LevelAdmin
}

func generateToken() string {
	b := make([]byte, 32)
	rand.Read(b)
	return base64.URLEncoding.EncodeToString(b)
}

func hashPassword(password string) string {
	hash := sha256.Sum256([]byte(password))
	return hex.EncodeToString(hash[:])
}

func sendPasswordResetEmail(to, tempPassword string) {
	if emailConfig.SMTPHost == "" {
		log.Println("Email not configured, temporary password:", tempPassword)
		return
	}

	m := gomail.NewMessage()
	m.SetHeader("From", emailConfig.From)
	m.SetHeader("To", to)
	m.SetHeader("Subject", "Password Reset - App Gateway")
	m.SetBody("text/html", fmt.Sprintf(`
		<h2>Password Reset</h2>
		<p>Your temporary password is:</p>
		<p><strong>%s</strong></p>
		<p>Please login and change your password immediately.</p>
	`, tempPassword))

	d := gomail.NewDialer(emailConfig.SMTPHost, emailConfig.SMTPPort, emailConfig.From, emailConfig.Password)
	if err := d.DialAndSend(m); err != nil {
		log.Printf("Failed to send email: %v", err)
	}
}

// ============================================
// MAIN
// ============================================

func main() {
	// Initialize database with default config
	defaultConfig := DBConfig{
		Host:     "localhost",
		Port:     5432,
		User:     "postgres",
		Password: "yourpassword",
		DBName:   "gateway_db",
		MaxConns: 25,
		MinConns: 5,
	}

	if err := initDB(defaultConfig); err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	defer db.Close()

	// Initialize admin after a short delay
	go func() {
		time.Sleep(2 * time.Second)
		initializeDefaultAdmin(context.Background())
	}()

	// Authentication endpoints
	http.HandleFunc("/api/login", handleLogin)
	http.HandleFunc("/api/logout", handleLogout)
	http.HandleFunc("/api/forgot-password", handleForgotPassword)
	http.HandleFunc("/api/change-password", handleChangePassword)
	http.HandleFunc("/api/user/info", handleUserInfo)
	http.HandleFunc("/api/user/apps", handleUserApps)

	// Admin endpoints
	http.HandleFunc("/api/admin/users", handleAdminUsers)
	http.HandleFunc("/api/admin/users/create", handleCreateUser)
	http.HandleFunc("/api/admin/users/update", handleUpdateUser)
	http.HandleFunc("/api/admin/users/delete", handleDeleteUser)
	http.HandleFunc("/api/admin/apps", handleAdminApps)
	http.HandleFunc("/api/admin/apps/create", handleCreateApp)
	http.HandleFunc("/api/admin/apps/update", handleUpdateApp)
	http.HandleFunc("/api/admin/apps/delete", handleDeleteApp)
	http.HandleFunc("/api/admin/assign-app", handleAssignApp)

	// Admin database settings
	http.HandleFunc("/api/admin/db-settings", handleGetDBSettings)
	http.HandleFunc("/api/admin/db-settings/update", handleUpdateDBSettings)
	http.HandleFunc("/api/admin/db-settings/test", handleTestDBConnection)

	// Gateway API endpoints (for external apps to send data)
	http.HandleFunc("/api/gateway/ingest", handleIngestData)
	http.HandleFunc("/api/gateway/apps/", func(w http.ResponseWriter, r *http.Request) {
		if strings.Contains(r.URL.Path, "/data") {
			handleGetAppData(w, r)
		} else if strings.HasSuffix(r.URL.Path, "/tables") {
			handleListAppTables(w, r)
		}
	})

	// Shared component endpoints
	http.HandleFunc("/api/components", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			handleCreateComponent(w, r)
		} else {
			handleGetComponents(w, r)
		}
	})
	http.HandleFunc("/api/components/search", handleSearchComponents)

	// App proxy endpoints
	http.HandleFunc("/proxy/", handleProxy)

	// Serve static files
	fs := http.FileServer(http.Dir("./static"))
	http.Handle("/", fs)

	log.Println("╔═══════════════════════════════════════╗")
	log.Println("║   App Gateway with PostgreSQL        ║")
	log.Println("╚═══════════════════════════════════════╝")
	log.Println("  Server started on :8081")
	log.Println("  Database: PostgreSQL")
	log.Println("  Gateway API: /api/gateway/ingest")
	log.Println("  Components API: /api/components")
	log.Println("╚═══════════════════════════════════════╝")

	log.Fatal(http.ListenAndServe(":8081", nil))
}
```


### Key Features Added:

1. **PostgreSQL Integration**: Direct connection with pgxpool, no external API server needed[^3_2][^3_4]
2. **Dynamic Table Creation**: Apps can send data and tables are created automatically[^3_2]
3. **Shared Component Table**: Centralized component storage accessible by all apps[^3_1]
4. **Admin Database Settings**: Configure PostgreSQL from admin panel with connection testing[^3_1]
5. **Gateway API Endpoints**:
    - `POST /api/gateway/ingest` - Apps send data
    - `GET /api/gateway/apps/{app_name}/tables` - List app tables
    - `GET /api/gateway/apps/{app_name}/tables/{table_name}/data` - Get app data
6. **Component API**:
    - `POST /api/components` - Create component
    - `GET /api/components?category=x` - Get components
    - `GET /api/components/search?q=term` - Search components

### Required Dependencies:

```bash
go get github.com/jackc/pgx/v5
go get github.com/jackc/pgx/v5/pgxpool
go get golang.org/x/crypto/bcrypt
go get gopkg.in/gomail.v2
```

This implementation provides a complete centralized PostgreSQL database system where multiple external apps can dynamically create tables, share data, and access common components.[^3_3][^3_4][^3_2]

<div align="center">⁂</div>

[^3_1]: app.go

[^3_2]: https://stackoverflow.com/questions/47809287/create-postgresql-table-dynamically-in-golang

[^3_3]: https://www.glukhov.org/post/2025/11/multitenant-database-patterns/

[^3_4]: https://docs.activestate.com/activego/1.8/pkg/github.com/jackc/pgx/


---

# admin pannel  database setup option  frontend

I'll add the database settings section to your admin panel frontend. Here are the additions to your existing **index.html** file:[^4_1]

## 1. Add Database Settings Tab (in the tabs section)

Find this section in your HTML:

```html
<div class="tabs">
    <div class="tab active" onclick="switchTab('users')">Users</div>
    <div class="tab" onclick="switchTab('apps')">Applications</div>
    <div class="tab" onclick="switchTab('assignments')">App Assignments</div>
</div>
```

**Replace with:**

```html
<div class="tabs">
    <div class="tab active" onclick="switchTab('users')">Users</div>
    <div class="tab" onclick="switchTab('apps')">Applications</div>
    <div class="tab" onclick="switchTab('assignments')">App Assignments</div>
    <div class="tab" onclick="switchTab('database')">Database Settings</div>
    <div class="tab" onclick="switchTab('components')">Components</div>
</div>
```


## 2. Add Database Settings Tab Content (after assignments tab)

Add this after the `assignmentsTab` div:

```html
<!-- Database Settings Tab -->
<div class="tab-content" id="databaseTab">
    <div style="max-width: 700px;">
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
            <strong>⚠️ Warning:</strong> Changing database settings will restart the connection. Make sure the credentials are correct.
        </div>
        
        <div id="dbSettingsMessage" class="success-message hidden"></div>
        <div id="dbSettingsError" class="error-message hidden"></div>
        
        <form id="dbSettingsForm">
            <div class="form-group">
                <label>Host</label>
                <input type="text" id="dbHost" required placeholder="localhost">
            </div>
            
            <div class="form-group">
                <label>Port</label>
                <input type="number" id="dbPort" required placeholder="5432" value="5432">
            </div>
            
            <div class="form-group">
                <label>Username</label>
                <input type="text" id="dbUser" required placeholder="postgres">
            </div>
            
            <div class="form-group">
                <label>Password</label>
                <div style="position: relative;">
                    <input type="password" id="dbPassword" required placeholder="Enter database password" style="padding-right: 40px;">
                    <span class="password-toggle" onclick="togglePasswordVisibility('dbPassword', this)">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path class="eye-open" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle class="eye-open" cx="12" cy="12" r="3"></circle>
                            <path class="eye-closed" d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <line class="eye-closed" x1="3" y1="3" x2="21" y2="21" style="display: none;"></line>
                        </svg>
                    </span>
                </div>
            </div>
            
            <div class="form-group">
                <label>Database Name</label>
                <input type="text" id="dbName" required placeholder="gateway_db">
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="form-group">
                    <label>Max Connections</label>
                    <input type="number" id="dbMaxConns" required value="25" min="1" max="100">
                </div>
                
                <div class="form-group">
                    <label>Min Connections</label>
                    <input type="number" id="dbMinConns" required value="5" min="1" max="50">
                </div>
            </div>
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="button" class="btn btn-small" onclick="testDBConnection()" style="background: #17a2b8; color: white; flex: 1;">
                    <span id="testBtnText">🔌 Test Connection</span>
                </button>
                <button type="submit" class="btn btn-primary btn-small" style="flex: 1;">
                    💾 Save Settings
                </button>
            </div>
        </form>
        
        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
            <h4 style="margin: 0 0 15px 0; color: #1B365D;">Current Connection Status</h4>
            <div id="connectionStatus" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px;">
                <div><strong>Host:</strong> <span id="statusHost">-</span></div>
                <div><strong>Port:</strong> <span id="statusPort">-</span></div>
                <div><strong>Database:</strong> <span id="statusDB">-</span></div>
                <div><strong>User:</strong> <span id="statusUser">-</span></div>
                <div><strong>Max Conns:</strong> <span id="statusMaxConns">-</span></div>
                <div><strong>Min Conns:</strong> <span id="statusMinConns">-</span></div>
            </div>
        </div>
    </div>
</div>

<!-- Components Tab -->
<div class="tab-content" id="componentsTab">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <div style="flex: 1; max-width: 400px;">
            <input type="text" id="componentSearch" placeholder="Search components..." 
                   oninput="searchComponents()" 
                   style="width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px;">
        </div>
        <button class="btn btn-primary btn-small" onclick="showAddComponentModal()">
            ➕ Add Component
        </button>
    </div>
    
    <div style="margin-bottom: 15px;">
        <select id="categoryFilter" onchange="filterComponentsByCategory()" 
                style="padding: 8px 12px; border: 2px solid #e0e0e0; border-radius: 5px;">
            <option value="">All Categories</option>
            <option value="Microcontroller">Microcontrollers</option>
            <option value="Resistor">Resistors</option>
            <option value="Capacitor">Capacitors</option>
            <option value="IC">ICs</option>
            <option value="Connector">Connectors</option>
            <option value="Sensor">Sensors</option>
            <option value="Other">Other</option>
        </select>
    </div>
    
    <div id="componentsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px;">
        <div style="text-align: center; padding: 40px; color: #999;">Loading components...</div>
    </div>
</div>
```


## 3. Add Component Modal (after other modals)

Add this before the closing `</body>` tag:

```html
<!-- Component Modal -->
<div class="modal" id="componentModal">
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="componentModalTitle">Add Component</h3>
            <button class="close-btn" onclick="closeModal('componentModal')">&times;</button>
        </div>
        <form id="componentForm">
            <div class="form-group">
                <label>Component Name</label>
                <input type="text" id="compName" required placeholder="e.g., STM32F407VGT6">
            </div>
            
            <div class="form-group">
                <label>Category</label>
                <select id="compCategory" required>
                    <option value="">Select category</option>
                    <option value="Microcontroller">Microcontroller</option>
                    <option value="Resistor">Resistor</option>
                    <option value="Capacitor">Capacitor</option>
                    <option value="IC">IC</option>
                    <option value="Connector">Connector</option>
                    <option value="Sensor">Sensor</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Description</label>
                <textarea id="compDescription" rows="3" placeholder="Component description"></textarea>
            </div>
            
            <div class="form-group">
                <label>Datasheet URL</label>
                <input type="url" id="compDatasheet" placeholder="https://example.com/datasheet.pdf">
            </div>
            
            <div class="form-group">
                <label>Additional Metadata (JSON)</label>
                <textarea id="compMetadata" rows="4" placeholder='{"package": "LQFP100", "voltage": "3.3V"}'></textarea>
                <small style="color: #666; font-size: 12px;">Optional: Add custom properties in JSON format</small>
            </div>
            
            <button type="submit" class="btn btn-primary">Save Component</button>
        </form>
    </div>
</div>
```


## 4. Add JavaScript Functions (in the `<script>` section)

Add these functions at the end of your script section (before `</script>`):

```javascript
// ============================================
// DATABASE SETTINGS FUNCTIONS
// ============================================

async function loadDBSettings() {
    try {
        const response = await fetch('/api/admin/db-settings');
        if (response.ok) {
            const config = await response.json();
            
            // Populate form
            document.getElementById('dbHost').value = config.host || 'localhost';
            document.getElementById('dbPort').value = config.port || 5432;
            document.getElementById('dbUser').value = config.user || 'postgres';
            document.getElementById('dbName').value = config.dbname || 'gateway_db';
            document.getElementById('dbMaxConns').value = config.max_conns || 25;
            document.getElementById('dbMinConns').value = config.min_conns || 5;
            
            // Update status display
            document.getElementById('statusHost').textContent = config.host || '-';
            document.getElementById('statusPort').textContent = config.port || '-';
            document.getElementById('statusDB').textContent = config.dbname || '-';
            document.getElementById('statusUser').textContent = config.user || '-';
            document.getElementById('statusMaxConns').textContent = config.max_conns || '-';
            document.getElementById('statusMinConns').textContent = config.min_conns || '-';
        }
    } catch (error) {
        console.error('Failed to load DB settings:', error);
    }
}

async function testDBConnection() {
    const btn = document.getElementById('testBtnText');
    const originalText = btn.textContent;
    btn.textContent = '⏳ Testing...';
    
    hideMessages();
    
    const config = {
        host: document.getElementById('dbHost').value,
        port: parseInt(document.getElementById('dbPort').value),
        user: document.getElementById('dbUser').value,
        password: document.getElementById('dbPassword').value,
        dbname: document.getElementById('dbName').value,
        max_conns: parseInt(document.getElementById('dbMaxConns').value),
        min_conns: parseInt(document.getElementById('dbMinConns').value)
    };
    
    try {
        const response = await fetch('/api/admin/db-settings/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showDBMessage(result.message || '✅ Connection successful!', 'success');
        } else {
            showDBMessage(result.message || '❌ Connection failed', 'error');
        }
    } catch (error) {
        showDBMessage('❌ Connection test failed: ' + error.message, 'error');
    } finally {
        btn.textContent = originalText;
    }
}

document.getElementById('dbSettingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    hideMessages();
    
    const config = {
        host: document.getElementById('dbHost').value,
        port: parseInt(document.getElementById('dbPort').value),
        user: document.getElementById('dbUser').value,
        password: document.getElementById('dbPassword').value,
        dbname: document.getElementById('dbName').value,
        max_conns: parseInt(document.getElementById('dbMaxConns').value),
        min_conns: parseInt(document.getElementById('dbMinConns').value)
    };
    
    try {
        const response = await fetch('/api/admin/db-settings/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            const result = await response.json();
            showDBMessage('✅ ' + (result.message || 'Settings saved successfully!'), 'success');
            await loadDBSettings();
        } else {
            const error = await response.text();
            showDBMessage('❌ Failed to save settings: ' + error, 'error');
        }
    } catch (error) {
        showDBMessage('❌ Error: ' + error.message, 'error');
    }
});

function showDBMessage(msg, type) {
    const msgEl = document.getElementById(type === 'success' ? 'dbSettingsMessage' : 'dbSettingsError');
    msgEl.textContent = msg;
    msgEl.classList.remove('hidden');
    
    setTimeout(() => {
        msgEl.classList.add('hidden');
    }, 5000);
}

function hideMessages() {
    document.getElementById('dbSettingsMessage').classList.add('hidden');
    document.getElementById('dbSettingsError').classList.add('hidden');
}

// ============================================
// COMPONENTS FUNCTIONS
// ============================================

let allComponents = [];

async function loadComponents() {
    try {
        const response = await fetch('/api/components');
        if (response.ok) {
            allComponents = await response.json();
            renderComponents(allComponents);
        }
    } catch (error) {
        console.error('Failed to load components:', error);
    }
}

function renderComponents(components) {
    const grid = document.getElementById('componentsGrid');
    
    if (!components || components.length === 0) {
        grid.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">No components found</div>';
        return;
    }
    
    grid.innerHTML = components.map(comp => `
        <div class="component-card" style="background: white; border-radius: 10px; padding: 20px; border: 2px solid #e0e0e0; transition: all 0.3s;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                <h4 style="margin: 0; color: #1B365D; font-size: 16px;">${comp.name}</h4>
                <span style="background: linear-gradient(135deg, #C9313D 0%, #1B365D 100%); color: white; padding: 3px 8px; border-radius: 5px; font-size: 11px;">
                    ${comp.category}
                </span>
            </div>
            <p style="color: #666; font-size: 14px; margin: 10px 0; min-height: 40px;">
                ${comp.description || 'No description'}
            </p>
            ${comp.datasheet ? `
                <a href="${comp.datasheet}" target="_blank" style="color: #C9313D; text-decoration: none; font-size: 13px; display: inline-block; margin-bottom: 10px;">
                    📄 View Datasheet
                </a>
            ` : ''}
            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #999;">
                Added by: ${comp.created_by || 'system'}<br>
                ${new Date(comp.created_at).toLocaleDateString()}
            </div>
        </div>
    `).join('');
}

async function searchComponents() {
    const searchTerm = document.getElementById('componentSearch').value;
    
    if (!searchTerm) {
        renderComponents(allComponents);
        return;
    }
    
    try {
        const response = await fetch(`/api/components/search?q=${encodeURIComponent(searchTerm)}`);
        if (response.ok) {
            const results = await response.json();
            renderComponents(results);
        }
    } catch (error) {
        console.error('Search failed:', error);
    }
}

function filterComponentsByCategory() {
    const category = document.getElementById('categoryFilter').value;
    
    if (!category) {
        renderComponents(allComponents);
    } else {
        const filtered = allComponents.filter(comp => comp.category === category);
        renderComponents(filtered);
    }
}

function showAddComponentModal() {
    document.getElementById('componentForm').reset();
    openModal('componentModal');
}

document.getElementById('componentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const metadata = document.getElementById('compMetadata').value;
    let parsedMetadata = {};
    
    if (metadata) {
        try {
            parsedMetadata = JSON.parse(metadata);
        } catch (error) {
            alert('Invalid JSON in metadata field');
            return;
        }
    }
    
    const data = {
        name: document.getElementById('compName').value,
        category: document.getElementById('compCategory').value,
        description: document.getElementById('compDescription').value,
        datasheet: document.getElementById('compDatasheet').value,
        metadata: parsedMetadata
    };
    
    try {
        const response = await fetch('/api/components', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-App-Name': currentUser.username
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('componentModal');
            await loadComponents();
            alert('✅ Component added successfully!');
        } else {
            alert('❌ Failed to add component');
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
});

// Update loadAdminData to include DB settings and components
async function loadAdminData() {
    await Promise.all([loadUsers(), loadApps(), loadDBSettings(), loadComponents()]);
    renderAssignments();
}

// Update switchTab function to handle new tabs
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(tab + 'Tab').classList.add('active');
    
    // Load data when switching to database tab
    if (tab === 'database') {
        loadDBSettings();
    } else if (tab === 'components') {
        loadComponents();
    }
}
```


## 5. Add CSS Styles for Component Cards

Add this to your `<style>` section:

```css
.component-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(201, 49, 61, 0.2);
    border-color: #C9313D;
}

.component-card a:hover {
    text-decoration: underline;
}
```

This complete implementation adds:[^4_2][^4_3][^4_1]

1. **Database Settings Tab** - Configure PostgreSQL connection with test functionality
2. **Components Tab** - Shared component library with search and filtering
3. **Connection Status Display** - Shows current database configuration
4. **Test Connection** - Validates credentials before saving
5. **Component Management** - Add, search, and filter components by category

The UI integrates seamlessly with your existing admin panel design and connects to the backend API endpoints we created earlier.[^4_4]

<div align="center">⁂</div>

[^4_1]: index.html

[^4_2]: https://stackoverflow.com/questions/47809287/create-postgresql-table-dynamically-in-golang

[^4_3]: https://docs.activestate.com/activego/1.8/pkg/github.com/jackc/pgx/

[^4_4]: app.go


---

# 2025/12/15 22:29:10 Failed to connect to database:failed to ping database: failed to connect to `user=postgres database=gateway_db`: [::1]:5432 (localhost): server error: FATAL: database "gateway_db" does not exist (SQLSTATE 3D000)

The error shows that the PostgreSQL database `gateway_db` doesn't exist yet. Here are solutions to fix this:[^5_1][^5_2]

## Solution 1: Create Database Manually (Quick Fix)

Connect to PostgreSQL and create the database:

```bash
# Using psql command line
psql -U postgres -c "CREATE DATABASE gateway_db;"

# Or using createdb utility
createdb -U postgres gateway_db

# Or connect to postgres database first
psql -U postgres
CREATE DATABASE gateway_db;
\q
```


## Solution 2: Auto-Create Database in app.go (Recommended)

Modify your `app.go` to automatically create the database if it doesn't exist:[^5_2][^5_3]

**Replace the `initDB` function with this enhanced version:**

```go
func initDB(config DBConfig) error {
	var err error

	// First, try to connect to the target database
	connString := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/%s?sslmode=disable",
		config.User, config.Password, config.Host, config.Port, config.DBName,
	)

	poolConfig, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return fmt.Errorf("failed to parse config: %w", err)
	}

	poolConfig.MaxConns = config.MaxConns
	poolConfig.MinConns = config.MinConns
	poolConfig.MaxConnLifetime = time.Hour
	poolConfig.MaxConnIdleTime = 30 * time.Minute

	dbMux.Lock()
	defer dbMux.Unlock()

	if db != nil {
		db.Close()
	}

	db, err = pgxpool.NewWithConfig(context.Background(), poolConfig)
	if err == nil {
		// Try to ping the database
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		if err = db.Ping(ctx); err == nil {
			// Database exists and connection successful
			if err := createTables(ctx); err != nil {
				return fmt.Errorf("failed to create tables: %w", err)
			}
			log.Println("✓ PostgreSQL connected successfully")
			return nil
		}
	}

	// Database doesn't exist, so create it
	log.Printf("Database '%s' doesn't exist, attempting to create...", config.DBName)
	
	if err := createDatabaseIfNotExists(config); err != nil {
		return fmt.Errorf("failed to create database: %w", err)
	}

	// Now connect to the newly created database
	db, err = pgxpool.NewWithConfig(context.Background(), poolConfig)
	if err != nil {
		return fmt.Errorf("failed to create pool after database creation: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err = db.Ping(ctx); err != nil {
		return fmt.Errorf("failed to ping database after creation: %w", err)
	}

	// Create tables
	if err := createTables(ctx); err != nil {
		return fmt.Errorf("failed to create tables: %w", err)
	}

	log.Println("✓ Database created and connected successfully")
	return nil
}

// createDatabaseIfNotExists connects to 'postgres' database and creates the target database
func createDatabaseIfNotExists(config DBConfig) error {
	// Connect to the default 'postgres' database
	connString := fmt.Sprintf(
		"postgres://%s:%s@%s:%d/postgres?sslmode=disable",
		config.User, config.Password, config.Host, config.Port,
	)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := pgx.Connect(ctx, connString)
	if err != nil {
		return fmt.Errorf("failed to connect to postgres database: %w", err)
	}
	defer conn.Close(ctx)

	// Check if database exists
	var exists bool
	query := "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)"
	err = conn.QueryRow(ctx, query, config.DBName).Scan(&exists)
	if err != nil {
		return fmt.Errorf("failed to check if database exists: %w", err)
	}

	if exists {
		log.Printf("Database '%s' already exists", config.DBName)
		return nil
	}

	// Create database (must use Identifier to properly quote the database name)
	createDBQuery := fmt.Sprintf("CREATE DATABASE %s", pgx.Identifier{config.DBName}.Sanitize())
	_, err = conn.Exec(ctx, createDBQuery)
	if err != nil {
		return fmt.Errorf("failed to create database: %w", err)
	}

	log.Printf("✓ Database '%s' created successfully", config.DBName)
	return nil
}
```


## Solution 3: Update main() with Better Error Handling

**Replace the database initialization in `main()` with:**

```go
func main() {
	// Initialize database with default config
	defaultConfig := DBConfig{
		Host:     getEnv("DB_HOST", "localhost"),
		Port:     getEnvInt("DB_PORT", 5432),
		User:     getEnv("DB_USER", "postgres"),
		Password: getEnv("DB_PASSWORD", "yourpassword"),
		DBName:   getEnv("DB_NAME", "gateway_db"),
		MaxConns: int32(getEnvInt("DB_MAX_CONNS", 25)),
		MinConns: int32(getEnvInt("DB_MIN_CONNS", 5)),
	}

	log.Println("╔═══════════════════════════════════════╗")
	log.Println("║   Initializing Database Connection   ║")
	log.Println("╚═══════════════════════════════════════╝")
	log.Printf("  Host: %s:%d", defaultConfig.Host, defaultConfig.Port)
	log.Printf("  Database: %s", defaultConfig.DBName)
	log.Printf("  User: %s", defaultConfig.User)

	if err := initDB(defaultConfig); err != nil {
		log.Printf("⚠️  Database connection failed: %v", err)
		log.Println("⚠️  Please ensure PostgreSQL is running and credentials are correct")
		log.Println("⚠️  You can manually create the database with:")
		log.Printf("     psql -U postgres -c \"CREATE DATABASE %s;\"", defaultConfig.DBName)
		log.Fatal("Exiting...")
	}
	defer db.Close()

	// Rest of your main function...
}

// Helper functions for environment variables
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
```

**Add import for strconv:**

```go
import (
	// ... existing imports
	"strconv"
)
```


## Solution 4: Using Environment Variables

Create a `.env` file or set environment variables:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=yourpassword
export DB_NAME=gateway_db
export DB_MAX_CONNS=25
export DB_MIN_CONNS=5
```


## Solution 5: Quick Shell Script

Create a `setup_db.sh` file:[^5_2]

```bash
#!/bin/bash

DB_NAME="gateway_db"
DB_USER="postgres"

echo "Checking if database exists..."

# Check if database exists
DB_EXISTS=$(psql -U $DB_USER -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" != "1" ]; then
    echo "Creating database $DB_NAME..."
    createdb -U $DB_USER $DB_NAME
    echo "✓ Database $DB_NAME created successfully"
else
    echo "✓ Database $DB_NAME already exists"
fi

echo "Starting application..."
go run app.go
```

Make it executable:

```bash
chmod +x setup_db.sh
./setup_db.sh
```


## Recommended Approach

Use **Solution 2** (auto-create database in app.go) as it handles the database creation automatically and provides a better user experience. The app will:[^5_3][^5_2]

1. Try to connect to the target database
2. If it doesn't exist, connect to the default `postgres` database
3. Check if the target database exists
4. Create it if needed
5. Connect to the newly created database
6. Create all necessary tables

This way, your application will work out-of-the-box without requiring manual database setup.[^5_1][^5_3]
<span style="display:none">[^5_10][^5_4][^5_5][^5_6][^5_7][^5_8][^5_9]</span>

<div align="center">⁂</div>

[^5_1]: https://www.commandprompt.com/education/postgresql-create-database-if-not-exists/

[^5_2]: https://stackoverflow.com/questions/18389124/simulate-create-database-if-not-exists-for-postgresql

[^5_3]: https://stackoverflow.com/questions/16501971/create-a-postgresql-database-programmatically

[^5_4]: https://www.postgresql.org/docs/current/sql-createdatabase.html

[^5_5]: https://www.w3resource.com/PostgreSQL/snippets/postgresql-create-database-if-not-exists.php

[^5_6]: https://commandprompt.com/education/postgresql-create-database-if-not-exists/

[^5_7]: https://stackoverflow.com/questions/3847945/how-do-you-connect-to-a-recently-create-postgres-database

[^5_8]: https://octopus.com/integrations/postgresql/postgres-create-database-if-not-exists

[^5_9]: https://docs.oracle.com/en/cloud/paas/autonomous-database/csgru/create-programmatic-dynamic-forms.html

[^5_10]: https://stackoverflow.com/questions/30641512/create-database-from-command-line-in-postgresql


---

# i want add new web app to Database Settings  how i wll add

I'll show you how to add a new web app through the Admin Panel interface. Here's the complete step-by-step guide:

## Step-by-Step: Add New Web App to Gateway

### 1. Access Admin Panel

1. **Login** to your gateway application (http://localhost:8081)
2. Click on your **user avatar** (top-right corner)
3. Select **"Admin Panel"** from the dropdown menu[^6_1]

### 2. Add New Application

1. In the Admin Panel, click on the **"Applications"** tab
2. Click the **"Add New App"** button[^6_1]
3. Fill in the application form:
```
App Name:        My Sensor App
URL:             http://localhost:3000
Description:     IoT sensor data collection application
Icon:            [Upload icon image or leave blank for default]
```

4. Click **"Save"** button
5. **Important**: Copy the **API Password** shown after creation - you'll need this!

### 3. Configure Your New Web App to Send Data

In your new web application, use these API endpoints to send data to the centralized gateway:

#### Example: Send Data from Your App

```javascript
// In your new web application (e.g., sensor app)

const GATEWAY_URL = 'http://localhost:8081';
const APP_NAME = 'my_sensor_app';  // Unique name for your app

// Function to send data to gateway
async function sendDataToGateway(tableName, data) {
    try {
        const response = await fetch(`${GATEWAY_URL}/api/gateway/ingest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                app_name: APP_NAME,
                table_name: tableName,
                data: data
            })
        });
        
        const result = await response.json();
        console.log('Data saved:', result);
        return result;
    } catch (error) {
        console.error('Failed to send data:', error);
    }
}

// Usage Example 1: Send temperature sensor data
await sendDataToGateway('temperature_logs', {
    temperature: 25.5,
    humidity: 60.2,
    location: 'Room_A',
    sensor_id: 'TEMP001'
});

// Usage Example 2: Send user activity data
await sendDataToGateway('user_activities', {
    user_id: 12345,
    action: 'button_click',
    page: '/dashboard',
    timestamp: new Date().toISOString()
});
```


#### Python Example

```python
import requests
import json
from datetime import datetime

GATEWAY_URL = 'http://localhost:8081'
APP_NAME = 'my_sensor_app'

def send_data_to_gateway(table_name, data):
    payload = {
        'app_name': APP_NAME,
        'table_name': table_name,
        'data': data
    }
    
    response = requests.post(
        f'{GATEWAY_URL}/api/gateway/ingest',
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    return response.json()

# Usage Example
result = send_data_to_gateway('temperature_logs', {
    'temperature': 25.5,
    'humidity': 60.2,
    'location': 'Room_A',
    'sensor_id': 'TEMP001'
})
print(result)
```


#### Go Example

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

const (
    GATEWAY_URL = "http://localhost:8081"
    APP_NAME    = "my_sensor_app"
)

type GatewayData struct {
    AppName   string                 `json:"app_name"`
    TableName string                 `json:"table_name"`
    Data      map[string]interface{} `json:"data"`
}

func sendDataToGateway(tableName string, data map[string]interface{}) error {
    payload := GatewayData{
        AppName:   APP_NAME,
        TableName: tableName,
        Data:      data,
    }
    
    jsonData, _ := json.Marshal(payload)
    
    resp, err := http.Post(
        GATEWAY_URL+"/api/gateway/ingest",
        "application/json",
        bytes.NewBuffer(jsonData),
    )
    
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    
    fmt.Println("Data sent successfully")
    return nil
}

func main() {
    // Usage Example
    data := map[string]interface{}{
        "temperature": 25.5,
        "humidity":    60.2,
        "location":    "Room_A",
        "sensor_id":   "TEMP001",
    }
    
    sendDataToGateway("temperature_logs", data)
}
```


### 4. Access Shared Components (Optional)

Your app can also use the shared component library:

```javascript
// Get all components
async function getComponents(category = '') {
    const url = category 
        ? `${GATEWAY_URL}/api/components?category=${category}`
        : `${GATEWAY_URL}/api/components`;
    
    const response = await fetch(url);
    return await response.json();
}

// Add a component
async function addComponent(component) {
    const response = await fetch(`${GATEWAY_URL}/api/components`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-App-Name': APP_NAME
        },
        body: JSON.stringify(component)
    });
    
    return await response.json();
}

// Usage
const components = await getComponents('Microcontroller');
console.log(components);

// Add new component
await addComponent({
    name: 'STM32F407VGT6',
    category: 'Microcontroller',
    description: 'ARM Cortex-M4 MCU',
    datasheet: 'https://example.com/datasheet.pdf',
    metadata: {
        package: 'LQFP100',
        voltage: '3.3V',
        flash: '512KB'
    }
});
```


### 5. Retrieve Data from Another App

Apps can access each other's data:

```javascript
// Get data from another app's table
async function getAppData(appName, tableName, limit = 100) {
    const response = await fetch(
        `${GATEWAY_URL}/api/gateway/apps/${appName}/tables/${tableName}/data?limit=${limit}`
    );
    
    return await response.json();
}

// Usage: Access sensor data from another app
const sensorData = await getAppData('iot_sensor_app', 'temperature_logs', 50);
console.log(sensorData);
```


### 6. Assign App to Users

1. In Admin Panel, go to **"App Assignments"** tab
2. Type username in the search box
3. Check/uncheck apps to assign/revoke access
4. Users will see assigned apps in their dashboard[^6_1]

## Complete Integration Example

Here's a complete HTML page example for your new web app:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Sensor Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        button { background: #C9313D; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #1B365D; }
        input { padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; width: 200px; }
    </style>
</head>
<body>
    <h1>Sensor Dashboard</h1>
    
    <div class="card">
        <h2>Send Sensor Data</h2>
        <input type="number" id="temperature" placeholder="Temperature" step="0.1">
        <input type="number" id="humidity" placeholder="Humidity" step="0.1">
        <input type="text" id="location" placeholder="Location">
        <button onclick="sendSensorData()">Send Data</button>
        <div id="status"></div>
    </div>
    
    <div class="card">
        <h2>Recent Data</h2>
        <button onclick="loadRecentData()">Refresh</button>
        <div id="dataList"></div>
    </div>
    
    <script>
        const GATEWAY_URL = 'http://localhost:8081';
        const APP_NAME = 'sensor_dashboard';
        
        async function sendSensorData() {
            const data = {
                temperature: parseFloat(document.getElementById('temperature').value),
                humidity: parseFloat(document.getElementById('humidity').value),
                location: document.getElementById('location').value,
                timestamp: new Date().toISOString()
            };
            
            try {
                const response = await fetch(`${GATEWAY_URL}/api/gateway/ingest`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        app_name: APP_NAME,
                        table_name: 'temperature_logs',
                        data: data
                    })
                });
                
                const result = await response.json();
                document.getElementById('status').innerHTML = 
                    `<p style="color: green;">✓ Data saved successfully!</p>`;
                
                // Clear inputs
                document.getElementById('temperature').value = '';
                document.getElementById('humidity').value = '';
                document.getElementById('location').value = '';
                
                loadRecentData();
            } catch (error) {
                document.getElementById('status').innerHTML = 
                    `<p style="color: red;">✗ Error: ${error.message}</p>`;
            }
        }
        
        async function loadRecentData() {
            try {
                const response = await fetch(
                    `${GATEWAY_URL}/api/gateway/apps/${APP_NAME}/tables/temperature_logs/data?limit=10`
                );
                
                const result = await response.json();
                const dataList = document.getElementById('dataList');
                
                if (result.data && result.data.length > 0) {
                    dataList.innerHTML = '<table style="width: 100%; border-collapse: collapse;">' +
                        '<tr style="background: #f0f0f0;"><th>Temp</th><th>Humidity</th><th>Location</th><th>Time</th></tr>' +
                        result.data.map(row => `
                            <tr>
                                <td>${row.temperature}°C</td>
                                <td>${row.humidity}%</td>
                                <td>${row.location}</td>
                                <td>${new Date(row.timestamp).toLocaleString()}</td>
                            </tr>
                        `).join('') +
                        '</table>';
                } else {
                    dataList.innerHTML = '<p>No data yet</p>';
                }
            } catch (error) {
                console.error('Failed to load data:', error);
            }
        }
        
        // Load data on page load
        loadRecentData();
    </script>
</body>
</html>
```


## Summary

1. **Add app via Admin Panel** → Applications tab → Add New App
2. **Copy API password** (if using authentication)
3. **Configure your app** to send data to `/api/gateway/ingest`
4. **Tables are created automatically** based on your data structure
5. **Apps can share data** by querying each other's tables
6. **Use shared components** library for common resources

The gateway automatically creates tables based on the data structure you send, so you don't need to manually configure the database schema ![^6_2][^6_3][^6_4]
<span style="display:none">[^6_10][^6_11][^6_12][^6_13][^6_14][^6_5][^6_6][^6_7][^6_8][^6_9]</span>

<div align="center">⁂</div>

[^6_1]: index.html

[^6_2]: app.go

[^6_3]: https://stackoverflow.com/questions/18389124/simulate-create-database-if-not-exists-for-postgresql

[^6_4]: https://stackoverflow.com/questions/16501971/create-a-postgresql-database-programmatically

[^6_5]: https://dribbble.com/search/admin-form

[^6_6]: https://colorlib.com/wp/free-admin-templates/

[^6_7]: https://www.jetadmin.io/admin-panel

[^6_8]: https://www.jotform.com/form-templates/category/application-form

[^6_9]: https://wpjobboard.net/kb/managing-applications-in-admin-panel/

[^6_10]: https://www.youtube.com/watch?v=__o-9F9NBjg

[^6_11]: https://www.youtube.com/watch?v=RTJOxkrbIPM

[^6_12]: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-expose-web-apis

[^6_13]: https://five.co/blog/the-admin-panel-the-best-web-app-template/

[^6_14]: https://blog.dreamfactory.com/what-is-api-gateway-authentication


---

# admin pannel add new Application is not working

I found the issue! The problem is in the `loadAdminData` function. It's calling the wrong `loadApps` function. There are two different functions with similar names, and it's loading the user apps instead of admin apps. Here's the fix:

## Fix for "Add New Application" Issue

**Find this function in your index.html (around the loadAdminData section):**

```javascript
async function loadAdminData() {
    await Promise.all([loadUsers(), loadApps(), loadDBSettings(), loadComponents()]);
    renderAssignments();
}
```

**Replace it with:**

```javascript
async function loadAdminData() {
    await Promise.all([loadUsers(), loadAdminApps(), loadDBSettings(), loadComponents()]);
    renderAssignments();
}

// Add this new function to load admin apps
async function loadAdminApps() {
    try {
        const response = await fetch('/api/admin/apps');
        if (response.ok) {
            allApps = await response.json();
            renderAppsTable();
        }
    } catch (error) {
        console.error('Failed to load admin apps:', error);
    }
}
```

**Also, update the appForm submit handler to call the correct function:**

Find this code:

```javascript
document.getElementById('appForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('appName').value,
        url: document.getElementById('appUrl').value,
        description: document.getElementById('appDescription').value,
        icon: currentAppIcon
    };
    
    const endpoint = editingAppId ? '/api/admin/apps/update' : '/api/admin/apps/create';
    if (editingAppId) data.id = editingAppId;
    
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (response.ok) {
        closeModal('appModal');
        await loadApps(); // <-- This is calling the wrong function!
        
        if (document.getElementById('appContainer').classList.contains('active')) {
            await loadUserApps();
        }
    }
});
```

**Replace the form handler with this:**

```javascript
document.getElementById('appForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('appName').value,
        url: document.getElementById('appUrl').value,
        description: document.getElementById('appDescription').value,
        icon: currentAppIcon
    };
    
    const endpoint = editingAppId ? '/api/admin/apps/update' : '/api/admin/apps/create';
    if (editingAppId) data.id = editingAppId;
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Show API password for new apps
            if (!editingAppId && result.api_password) {
                alert(`✅ App created successfully!\n\n🔑 API Password: ${result.api_password}\n\n⚠️ Save this password - you won't see it again!`);
            }
            
            closeModal('appModal');
            await loadAdminApps(); // Load admin apps table
            renderAssignments(); // Refresh assignments
        } else {
            const error = await response.text();
            alert('❌ Failed to create app: ' + error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error creating app: ' + error.message);
    }
});
```


## Complete Fixed Section

Here's the complete section to replace in your `<script>` tag:

```javascript
// ============================================
// ADMIN DATA LOADING
// ============================================

async function loadAdminData() {
    await Promise.all([loadUsers(), loadAdminApps(), loadDBSettings(), loadComponents()]);
    renderAssignments();
}

async function loadAdminApps() {
    try {
        const response = await fetch('/api/admin/apps');
        if (response.ok) {
            allApps = await response.json();
            renderAppsTable();
        }
    } catch (error) {
        console.error('Failed to load admin apps:', error);
        alert('Failed to load applications');
    }
}

// App Form Submit Handler
document.getElementById('appForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('appName').value,
        url: document.getElementById('appUrl').value,
        description: document.getElementById('appDescription').value,
        icon: currentAppIcon
    };
    
    const endpoint = editingAppId ? '/api/admin/apps/update' : '/api/admin/apps/create';
    if (editingAppId) data.id = editingAppId;
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Show API password for new apps
            if (!editingAppId && result.api_password) {
                const copyText = `App: ${result.name}\nURL: ${result.url}\nAPI Password: ${result.api_password}`;
                
                // Try to copy to clipboard
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(result.api_password);
                    alert(`✅ App created successfully!\n\n🔑 API Password: ${result.api_password}\n\n📋 Password copied to clipboard!\n⚠️ Save this password - you won't see it again!`);
                } else {
                    alert(`✅ App created successfully!\n\n🔑 API Password: ${result.api_password}\n\n⚠️ Save this password - you won't see it again!`);
                }
            } else {
                alert('✅ App updated successfully!');
            }
            
            closeModal('appModal');
            await loadAdminApps();
            renderAssignments();
        } else {
            const error = await response.text();
            alert('❌ Failed to save app: ' + error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('❌ Error: ' + error.message);
    }
});
```


## Summary of Changes

1. **Created `loadAdminApps()` function** - Properly loads apps for the admin panel
2. **Updated `loadAdminData()`** - Now calls the correct function
3. **Fixed appForm submit** - Added proper error handling and shows the API password when creating new apps
4. **Added clipboard copy** - Automatically copies the API password to clipboard

After making these changes, the "Add New Application" button should work correctly, and you'll see:

- The modal opens properly ✅
- Form submits successfully ✅
- Apps table updates automatically ✅
- API password is shown and copied ✅

Try it now and let me know if it works![^7_1][^7_2]

<div align="center">⁂</div>

[^7_1]: app.go

[^7_2]: index.html


---

# still same

Let me help you debug this properly. Let's check what's actually happening and fix it step by step.

## Step 1: Check Browser Console

First, open your browser's Developer Tools (F12) and check the Console tab. Look for any errors when you:

1. Click "Add New App" button
2. Fill the form
3. Click Save

## Step 2: Complete Debugging Fix

Replace the entire apps-related JavaScript section with this debugged version:

```javascript
// ============================================
// ADMIN APPS MANAGEMENT - FIXED WITH DEBUGGING
// ============================================

function showCreateAppModal() {
    console.log('Opening create app modal...');
    editingAppId = null;
    document.getElementById('appModalTitle').textContent = 'Add Application';
    document.getElementById('appForm').reset();
    document.getElementById('iconPreview').innerHTML = '';
    currentAppIcon = null;
    openModal('appModal');
    console.log('Modal opened');
}

function editApp(appId) {
    console.log('Editing app:', appId);
    const app = allApps.find(a => a.id === appId);
    if (!app) {
        console.error('App not found:', appId);
        return;
    }
    
    editingAppId = appId;
    document.getElementById('appModalTitle').textContent = 'Edit Application';
    document.getElementById('appName').value = app.name;
    document.getElementById('appUrl').value = app.url;
    document.getElementById('appDescription').value = app.description;
    currentAppIcon = app.icon;
    
    if (app.icon) {
        document.getElementById('iconPreview').innerHTML = 
            `<img src="${app.icon}" style="width: 64px; height: 64px; border-radius: 8px;">`;
    }
    
    openModal('appModal');
}

async function deleteApp(appId) {
    if (!confirm('Delete this app?')) return;
    
    try {
        const response = await fetch(`/api/admin/apps/delete?id=${appId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('✅ App deleted successfully!');
            await loadAdminApps();
            renderAssignments();
        } else {
            alert('❌ Failed to delete app');
        }
    } catch (error) {
        console.error('Error deleting app:', error);
        alert('❌ Error: ' + error.message);
    }
}

async function loadAdminApps() {
    console.log('Loading admin apps...');
    try {
        const response = await fetch('/api/admin/apps');
        console.log('Admin apps response status:', response.status);
        
        if (response.ok) {
            allApps = await response.json();
            console.log('Loaded apps:', allApps);
            renderAppsTable();
        } else {
            const errorText = await response.text();
            console.error('Failed to load apps:', errorText);
            alert('Failed to load applications: ' + errorText);
        }
    } catch (error) {
        console.error('Error loading admin apps:', error);
        alert('Error loading applications: ' + error.message);
    }
}

function renderAppsTable() {
    console.log('Rendering apps table...');
    const tbody = document.querySelector('#appsTable tbody');
    
    if (!allApps || allApps.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #999;">No applications yet</td></tr>';
        return;
    }
    
    tbody.innerHTML = allApps.map(app => `
        <tr>
            <td>${app.name}</td>
            <td>${app.url}</td>
            <td>${app.description || '-'}</td>
            <td>
                <button class="btn btn-edit btn-small" onclick="editApp('${app.id}')">Edit</button>
                <button class="btn btn-delete btn-small" onclick="deleteApp('${app.id}')">Delete</button>
            </td>
        </tr>
    `).join('');
    
    console.log('Apps table rendered with', allApps.length, 'apps');
}

// App Form Submit Handler - Place this AFTER the form element exists
setTimeout(() => {
    const appForm = document.getElementById('appForm');
    
    if (!appForm) {
        console.error('App form not found!');
        return;
    }
    
    console.log('Setting up app form submit handler...');
    
    appForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log('App form submitted');
        
        const nameInput = document.getElementById('appName');
        const urlInput = document.getElementById('appUrl');
        const descInput = document.getElementById('appDescription');
        
        console.log('Form values:', {
            name: nameInput?.value,
            url: urlInput?.value,
            desc: descInput?.value
        });
        
        const data = {
            name: nameInput.value,
            url: urlInput.value,
            description: descInput.value,
            icon: currentAppIcon
        };
        
        const endpoint = editingAppId ? '/api/admin/apps/update' : '/api/admin/apps/create';
        if (editingAppId) data.id = editingAppId;
        
        console.log('Sending request to:', endpoint);
        console.log('Data:', data);
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            console.log('Response status:', response.status);
            
            if (response.ok) {
                const result = await response.json();
                console.log('Success result:', result);
                
                // Show API password for new apps
                if (!editingAppId && result.api_password) {
                    const message = `✅ App created successfully!\n\n` +
                                  `🔑 API Password: ${result.api_password}\n\n` +
                                  `⚠️ IMPORTANT: Save this password!\n` +
                                  `You won't be able to see it again.`;
                    
                    // Try to copy to clipboard
                    try {
                        await navigator.clipboard.writeText(result.api_password);
                        alert(message + '\n\n📋 Password copied to clipboard!');
                    } catch (err) {
                        alert(message);
                    }
                } else {
                    alert('✅ App updated successfully!');
                }
                
                closeModal('appModal');
                await loadAdminApps();
                renderAssignments();
            } else {
                const error = await response.text();
                console.error('Server error:', error);
                alert('❌ Failed to save app: ' + error);
            }
        } catch (error) {
            console.error('Request error:', error);
            alert('❌ Network error: ' + error.message);
        }
    });
    
    console.log('App form handler installed');
}, 1000);
```


## Step 3: Check Backend - Verify app.go has correct handler

Make sure your `main()` function in app.go has this line:

```go
http.HandleFunc("/api/admin/apps/create", handleCreateApp)
```

And check that `handleCreateApp` looks like this:

```go
func handleCreateApp(w http.ResponseWriter, r *http.Request) {
    // Check method
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    
    session, err := getSession(r)
    if err != nil || !isAdmin(r.Context(), session.Username) {
        log.Printf("Unauthorized access attempt")
        http.Error(w, "Unauthorized", http.StatusUnauthorized)
        return
    }

    var req App
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        log.Printf("Failed to decode request: %v", err)
        http.Error(w, "Invalid request", http.StatusBadRequest)
        return
    }

    log.Printf("Creating app: %s at %s", req.Name, req.URL)

    req.ID = generateToken()[:8]
    req.CreatedAt = time.Now()

    apiPassword := generateToken()[:16]
    req.Password = hashPassword(apiPassword)

    if err := saveApp(r.Context(), &req); err != nil {
        log.Printf("Failed to save app: %v", err)
        http.Error(w, "Failed to create app", http.StatusInternalServerError)
        return
    }

    response := map[string]interface{}{
        "id":           req.ID,
        "name":         req.Name,
        "url":          req.URL,
        "icon":         req.Icon,
        "description":  req.Description,
        "created_at":   req.CreatedAt,
        "api_password": apiPassword,
    }

    log.Printf("App created successfully: %s", req.ID)
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
}
```


## Step 4: Test Step by Step

After applying the fixes:

1. **Restart your Go server**
2. **Clear browser cache** (Ctrl+Shift+Delete)
3. **Reload the page** (Ctrl+F5)
4. **Open Developer Console** (F12)
5. **Try adding an app** and watch the console

You should see these logs:

```
Opening create app modal...
Modal opened
App form submitted
Form values: {...}
Sending request to: /api/admin/apps/create
Response status: 200
Success result: {...}
```


## Step 5: If still not working, tell me:

1. **What errors appear in the browser console?**
2. **What do you see in the Go server terminal?**
3. **Does the modal open when you click "Add New App"?**
4. **What happens when you click the Save button?**

This will help me pinpoint the exact issue!

