<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Обработка OPTIONS запроса для CORS
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Секретный ключ
define('API_KEY', 'GBpk54ey547h54');

// Проверка ключа
if (!isset($_GET['key']) || $_GET['key'] !== API_KEY) {
    echo json_encode(["error" => "Доступ запрещен"]);
    exit;
}

// Подключение к БД
$mysqli = new mysqli("localhost", "ook", "LqDP2vrZznr8vxJI7RzN", "ook");
if ($mysqli->connect_errno) {
    echo json_encode(["error" => $mysqli->connect_error]);
    exit;
}

$action = $_GET['action'] ?? 'help';

// 📌 Справка по API
if ($action === 'help') {
    echo json_encode([
        "api_name" => "5play.dev Database API",
        "version" => "2.0",
        "endpoints" => [
            "get_posts" => "GET ?action=get_posts&key=API_KEY - Получить все записи dle_post",
            "get_google_play_data" => "GET ?action=get_google_play_data&key=API_KEY - Получить данные для Google Play Links",
            "update_post" => "POST ?action=update_post&key=API_KEY - Обновить запись",
            "check_version" => "GET ?action=check_version&id=ID&key=API_KEY - Проверить версию в apk-original",
            "update_file" => "POST ?action=update_file&key=API_KEY - Обновить файл в dle_files",
            "get_post" => "GET ?action=get_post&id=ID&key=API_KEY - Получить запись по ID",
            "update_version" => "POST ?action=update_version&key=API_KEY - Обновить версию игры",
            "check_apk_original" => "GET ?action=check_apk_original&id=ID&version=VERSION&key=API_KEY - Проверить версию в apk-original для parser1",
            "add_dle_file" => "POST ?action=add_dle_file&key=API_KEY - Добавить файл в dle_files",
            "update_dle_file" => "POST ?action=update_dle_file&key=API_KEY - Обновить файл в dle_files",
            "update_apk_original" => "POST ?action=update_apk_original&key=API_KEY - Обновить apk-original в dle_post",
            "add_tracking" => "POST ?action=add_tracking&key=API_KEY - Добавить в таблицу отслеживания",
            "check_duplicate" => "GET ?action=check_duplicate&key=API_KEY - Проверить дубли файлов",
            "get_storage_info" => "GET ?action=get_storage_info&id=ID&key=API_KEY - Получить информацию о хранилище",
            "check_mod_at" => "GET ?action=check_mod_at&id=ID&version=VERSION&key=API_KEY - Проверить версию в mod-at для parser2",
            "check_duplicate_mod" => "GET ?action=check_duplicate_mod&key=API_KEY - Проверить дубли для модифицированных приложений",
            "add_tracking_mod" => "POST ?action=add_tracking_mod&key=API_KEY - Добавить в таблицу отслеживания модов",
            "update_mod_at" => "POST ?action=update_mod_at&key=API_KEY - Обновить поле mod-at в dle_post",
            "create_mod_tracking_table" => "GET ?action=create_mod_tracking_table&key=API_KEY - Создать таблицу отслеживания модов",
            "check_mod_table_structure" => "GET ?action=check_mod_table_structure&key=API_KEY - Проверить структуру таблицы file_tracking_mod",
            "update_dle_file" => "POST ?action=update_dle_file&key=API_KEY - Обновить файл в dle_files",
            "get_file_info" => "POST ?action=get_file_info&key=API_KEY - Получить информацию о файле из dle_files"
        ]
    ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

// 📌 Получение всех записей dle_post
if ($action === 'get_posts') {
    $query = "SELECT id, xfields, title FROM dle_post";
    $result = $mysqli->query($query);

    if (!$result) {
        echo json_encode(["error" => $mysqli->error]);
        exit;
    }

    $data = [];
    while ($row = $result->fetch_assoc()) {
        $data[] = $row;
    }

    echo json_encode([
        "success" => true,
        "count" => count($data),
        "data" => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// 📌 Получение данных для Google Play Links (аналог get_google_play_links.pl)
if ($action === 'get_google_play_data') {
    $query = "SELECT id, xfields FROM dle_post";
    $result = $mysqli->query($query);

    if (!$result) {
        echo json_encode(["error" => $mysqli->error]);
        exit;
    }

    $data = [];
    while ($row = $result->fetch_assoc()) {
        $id = $row['id'];
        $xfields = $row['xfields'];
        
        $gp_url = "-";
        $ver_game = "";

        // Если есть upppp — берём её
        if (preg_match('/\|\|upppp\|([^\|"\']+)/', $xfields, $matches)) {
            $gp_url = $matches[1];
        }
        // Иначе, если есть google_play_url — берём её
        elseif (preg_match('/\|\|google_play_url\|([^|]+)\|\|/', $xfields, $matches)) {
            $gp_url = $matches[1];
        }

        // Получаем версию игры
        if (preg_match('/\|\|ver_game\|([^|]+)\|\|/', $xfields, $matches)) {
            $ver_game = $matches[1];
        }

        if ($ver_game !== "") {
            $data[] = [
                "id" => $id,
                "gp_url" => $gp_url,
                "ver_game" => $ver_game
            ];
        } else {
            $data[] = [
                "id" => $id,
                "gp_url" => $gp_url
            ];
        }
    }

    echo json_encode([
        "success" => true,
        "count" => count($data),
        "data" => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// 📌 Проверка версии в apk-original
if ($action === 'check_version') {
    $id = intval($_GET['id'] ?? 0);
    $version = $_GET['version'] ?? '';
    
    if ($id <= 0 || !$version) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }

    $query = "SELECT xfields FROM dle_post WHERE id = ?";
    $stmt = $mysqli->prepare($query);
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        $xfields = $row['xfields'];
        
        // Ищем версию в apk-original
        if (preg_match('/\|\|apk-original\|([^|]+)\|\|/', $xfields, $matches)) {
            $apk_original = $matches[1];
            // Извлекаем версию из имени файла
            if (preg_match('/(\d+\.\d+\.?\d*)/', $apk_original, $version_matches)) {
                $current_version = $version_matches[1];
                
                // Простое сравнение версий
                $need_update = version_compare($current_version, $version) < 0;
                
                echo json_encode([
                    "success" => true,
                    "id" => $id,
                    "current_version" => $current_version,
                    "new_version" => $version,
                    "need_update" => $need_update,
                    "apk_original" => $apk_original
                ], JSON_UNESCAPED_UNICODE);
                exit;
            }
        }
        
        echo json_encode([
            "success" => true,
            "id" => $id,
            "current_version" => null,
            "new_version" => $version,
            "need_update" => true,
            "apk_original" => null
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Запись не найдена"]);
    }
    exit;
}

// 📌 Обновление записи (POST)
if ($action === 'update_post' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = intval($_POST['id'] ?? 0);
    $new_xfields = $_POST['xfields'] ?? '';
    $new_date = $_POST['date'] ?? '';
    $new_editdate = intval($_POST['editdate'] ?? 0);

    if ($id <= 0 || !$new_xfields || !$new_date || !$new_editdate) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }

    $stmt = $mysqli->prepare("
        UPDATE dle_post p
        LEFT JOIN dle_post_extras e ON p.id = e.news_id
        SET p.xfields = ?, p.date = ?, e.editdate = ?
        WHERE p.id = ?
    ");
    $stmt->bind_param("ssii", $new_xfields, $new_date, $new_editdate, $id);

    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "id" => $id,
            "message" => "Запись обновлена"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => $stmt->error]);
    }
    exit;
}

// 📌 Получение записи по ID
if ($action === 'get_post') {
    $id = intval($_GET['id'] ?? 0);
    
    if ($id <= 0) {
        echo json_encode(["error" => "Неверный ID"]);
        exit;
    }

    $query = "SELECT id, xfields, title FROM dle_post WHERE id = ?";
    $stmt = $mysqli->prepare($query);
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        echo json_encode([
            "success" => true,
            "data" => $row
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Запись не найдена"]);
    }
    exit;
}

// 📌 Обновление версии игры
if ($action === 'update_version' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = intval($_POST['id'] ?? 0);
    $new_version = $_POST['version'] ?? '';
    $new_date = $_POST['date'] ?? '';
    $new_editdate = intval($_POST['editdate'] ?? 0);

    if ($id <= 0 || !$new_version || !$new_date || !$new_editdate) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }

    // Получаем текущие данные
    $query = "SELECT xfields FROM dle_post WHERE id = ?";
    $stmt = $mysqli->prepare($query);
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if (!$row = $result->fetch_assoc()) {
        echo json_encode(["error" => "Запись не найдена"]);
        exit;
    }

    $xfields = $row['xfields'];
    
    // Обновляем версию в xfields
    $new_xfields = preg_replace(
        '/\|\|ver_game\|([^|]+)\|\|/',
        "||ver_game|$new_version||",
        $xfields
    );

    // Обновляем обе таблицы
    $update_stmt = $mysqli->prepare("
        UPDATE dle_post p
        LEFT JOIN dle_post_extras e ON p.id = e.news_id
        SET p.xfields = ?, p.date = ?, e.editdate = ?
        WHERE p.id = ?
    ");
    $update_stmt->bind_param("ssii", $new_xfields, $new_date, $new_editdate, $id);

    if ($update_stmt->execute()) {
        echo json_encode([
            "success" => true,
            "id" => $id,
            "old_xfields" => $xfields,
            "new_xfields" => $new_xfields,
            "message" => "Версия обновлена"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Ошибка обновления: " . $update_stmt->error]);
    }
    exit;
}

// 📌 Обновление файла в dle_files
if ($action === 'update_file' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $app_name = $_POST['app_name'] ?? '';
    $version = $_POST['version'] ?? '';
    $file_extension = $_POST['file_extension'] ?? '';
    $filename = $_POST['filename'] ?? '';
    $file_size = intval($_POST['file_size'] ?? 0);
    $checksum = $_POST['checksum'] ?? '';
    $download_dir = $_POST['download_dir'] ?? '';

    if ($news_id <= 0 || !$app_name || !$version || !$filename) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }

    // Обновляем или создаем запись в dle_files
    $stmt = $mysqli->prepare("
        INSERT INTO dle_files (news_id, name, size, checksum, path)
        VALUES (?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        size = VALUES(size),
        checksum = VALUES(checksum),
        path = VALUES(path)
    ");
    
    $file_path = $download_dir . '/' . $filename;
    $stmt->bind_param("isisss", $news_id, $filename, $file_size, $checksum, $file_path);

    if ($stmt->execute()) {
        $file_id = $mysqli->insert_id ?: $news_id; // Если обновление, используем news_id
        
        // Обновляем dle_post
        $update_stmt = $mysqli->prepare("
            UPDATE dle_post 
            SET xfields = REPLACE(xfields, '||apk-original||', CONCAT('||apk-original|', ?, '||'))
            WHERE id = ?
        ");
        $update_stmt->bind_param("si", $filename, $news_id);
        
        if ($update_stmt->execute()) {
            echo json_encode([
                "success" => true,
                "file_id" => $file_id,
                "news_id" => $news_id,
                "message" => "Файл обновлен"
            ], JSON_UNESCAPED_UNICODE);
        } else {
            echo json_encode(["error" => "Ошибка обновления dle_post: " . $update_stmt->error]);
        }
    } else {
        echo json_encode(["error" => "Ошибка обновления dle_files: " . $stmt->error]);
    }
    exit;
}

// 📌 Проверка версии в apk-original для parser1
if ($action === 'check_apk_original') {
    $news_id = intval($_GET['id'] ?? 0);
    $current_version = $_GET['version'] ?? '';
    
    if ($news_id <= 0 || !$current_version) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("SELECT xfields FROM dle_post WHERE id = ?");
    $stmt->bind_param("i", $news_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        $xfields = $row['xfields'];
        
        // Извлекаем версию из поля apk-original
        if (preg_match('/apk-original\|\[attachment=\d+:(.+?)\]/', $xfields, $matches)) {
            $attachment_name = $matches[1];
            
            // Извлекаем версию из имени attachment
            if (preg_match('/(\d+\.\d+(?:\.\d+)?)/', $attachment_name, $version_matches)) {
                $apk_original_version = $version_matches[1];
                
                // Сравниваем версии
                $need_update = version_compare($current_version, $apk_original_version) > 0;
                
                echo json_encode([
                    "success" => true,
                    "news_id" => $news_id,
                    "attachment_name" => $attachment_name,
                    "apk_original_version" => $apk_original_version,
                    "current_version" => $current_version,
                    "need_update" => $need_update,
                    "message" => $need_update ? "Нужно обновление" : "Версия актуальна"
                ], JSON_UNESCAPED_UNICODE);
            } else {
                echo json_encode([
                    "success" => true,
                    "news_id" => $news_id,
                    "attachment_name" => $attachment_name,
                    "apk_original_version" => null,
                    "current_version" => $current_version,
                    "need_update" => true,
                    "message" => "Не удалось извлечь версию из attachment"
                ], JSON_UNESCAPED_UNICODE);
            }
        } else {
            echo json_encode([
                "success" => true,
                "news_id" => $news_id,
                "attachment_name" => null,
                "apk_original_version" => null,
                "current_version" => $current_version,
                "need_update" => true,
                "message" => "Поле apk-original не содержит attachment"
            ], JSON_UNESCAPED_UNICODE);
        }
    } else {
        echo json_encode(["error" => "Новость не найдена"]);
    }
    exit;
}

// 📌 Добавление файла в dle_files
if ($action === 'add_dle_file' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $name = $_POST['name'] ?? '';
    $onserver = $_POST['onserver'] ?? '';
    $author = $_POST['author'] ?? 'sergeyAi';
    $date = $_POST['date'] ?? time();
    $dcount = intval($_POST['dcount'] ?? 0);
    $size = intval($_POST['size'] ?? 0);
    $checksum = $_POST['checksum'] ?? '';
    $driver = intval($_POST['driver'] ?? 2);
    $is_public = intval($_POST['is_public'] ?? 0);
    
    if ($news_id <= 0 || !$name || !$onserver) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("
        INSERT INTO dle_files (news_id, name, onserver, author, date, dcount, size, checksum, driver, is_public)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param("issiiiisis", $news_id, $name, $onserver, $author, $date, $dcount, $size, $checksum, $driver, $is_public);
    
    if ($stmt->execute()) {
        $file_id = $mysqli->insert_id;
        echo json_encode([
            "success" => true,
            "file_id" => $file_id,
            "message" => "Файл добавлен в dle_files"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Ошибка добавления в dle_files: " . $stmt->error]);
    }
    exit;
}

// 📌 Получение информации о файле из dle_files (parser2)
if ($action === 'get_file_info') {
    $file_id = intval($_POST['file_id'] ?? 0);
    
    if (!$file_id) {
        echo json_encode(["error" => "ID файла не указан"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("SELECT id, news_id, name, onserver, author, date, dcount, size, checksum, driver, is_public FROM dle_files WHERE id = ?");
    $stmt->bind_param("i", $file_id);
    $stmt->execute();
    $result = $stmt->get_result();
    $file_info = $result->fetch_assoc();
    
    if ($file_info) {
        echo json_encode([
            "success" => true,
            "file_info" => $file_info
        ]);
    } else {
        echo json_encode([
            "success" => false,
            "error" => "Файл с ID $file_id не найден"
        ]);
    }
    exit;
}

// 📌 Обновление файла в dle_files
if ($action === 'update_dle_file' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $file_id = intval($_POST['file_id'] ?? 0);
    $name = $_POST['name'] ?? '';
    $onserver = $_POST['onserver'] ?? '';
    $date = $_POST['date'] ?? time();
    $size = intval($_POST['size'] ?? 0);
    $checksum = $_POST['checksum'] ?? '';
    
    if ($file_id <= 0 || !$name || !$onserver) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("
        UPDATE dle_files 
        SET name = ?, onserver = ?, date = ?, size = ?, checksum = ?
        WHERE id = ?
    ");
    $stmt->bind_param("ssiisi", $name, $onserver, $date, $size, $checksum, $file_id);
    
    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "file_id" => $file_id,
            "message" => "Файл обновлен в dle_files"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Ошибка обновления dle_files: " . $stmt->error]);
    }
    exit;
}

// 📌 Обновление apk-original в dle_post
if ($action === 'update_apk_original' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $file_id = intval($_POST['file_id'] ?? 0);
    $app_name = $_POST['app_name'] ?? '';
    $version = $_POST['version'] ?? '';
    $file_extension = $_POST['file_extension'] ?? '';
    
    if ($news_id <= 0 || $file_id <= 0 || !$app_name || !$version) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    // Получаем текущие xfields
    $stmt = $mysqli->prepare("SELECT xfields FROM dle_post WHERE id = ?");
    $stmt->bind_param("i", $news_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        $xfields = $row['xfields'];
        
        // Транслитерация кириллицы
        $transliterated_name = transliterate_cyrillic($app_name);
        $readable_filename = $transliterated_name . ' ' . $version . $file_extension;
        
        // Формируем новый attachment
        $new_attachment = "[attachment={$file_id}:{$readable_filename}]";
        
        // Обновляем поле apk-original
        $pattern = '/apk-original\|[^|]*\|\|/';
        $replacement = 'apk-original|' . $new_attachment . '||';
        
        if (preg_match($pattern, $xfields)) {
            $new_xfields = preg_replace($pattern, $replacement, $xfields);
        } else {
            $new_xfields = $xfields . '||apk-original|' . $new_attachment . '||';
        }
        
        // Обновляем запись
        $update_stmt = $mysqli->prepare("UPDATE dle_post SET xfields = ? WHERE id = ?");
        $update_stmt->bind_param("si", $new_xfields, $news_id);
        
        if ($update_stmt->execute()) {
            echo json_encode([
                "success" => true,
                "news_id" => $news_id,
                "file_id" => $file_id,
                "attachment" => $new_attachment,
                "message" => "Поле apk-original обновлено"
            ], JSON_UNESCAPED_UNICODE);
        } else {
            echo json_encode(["error" => "Ошибка обновления dle_post: " . $update_stmt->error]);
        }
    } else {
        echo json_encode(["error" => "Новость не найдена"]);
    }
    exit;
}

// 📌 Добавление в таблицу отслеживания
if ($action === 'add_tracking' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $app_name = $_POST['app_name'] ?? '';
    $version = $_POST['version'] ?? '';
    $file_size = intval($_POST['file_size'] ?? 0);
    $file_path = $_POST['file_path'] ?? '';
    $checksum = $_POST['checksum'] ?? '';
    $sha256_hash = $_POST['sha256_hash'] ?? null;
    $package_name = $_POST['package_name'] ?? null;
    $source_priority = intval($_POST['source_priority'] ?? 0);
    $source_url = $_POST['source_url'] ?? '';
    
    if ($news_id <= 0 || !$app_name || !$version || !$file_path || !$checksum) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    // Создаем таблицу если не существует
    $create_table = "
        CREATE TABLE IF NOT EXISTS file_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            news_id INT NOT NULL,
            app_name VARCHAR(255) NOT NULL,
            version VARCHAR(100) NOT NULL,
            file_size BIGINT NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            checksum VARCHAR(32) NOT NULL,
            sha256_hash VARCHAR(64) NULL,
            package_name VARCHAR(255) NULL,
            source_priority INT DEFAULT 0,
            download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            source_url VARCHAR(500) NOT NULL,
            INDEX idx_news_id (news_id),
            INDEX idx_app_name (app_name),
            INDEX idx_sha256 (sha256_hash),
            INDEX idx_package_name (package_name),
            INDEX idx_source_priority (source_priority)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
    ";
    $mysqli->query($create_table);
    
    $stmt = $mysqli->prepare("
        INSERT INTO file_tracking (news_id, app_name, version, file_size, file_path, checksum, sha256_hash, package_name, source_priority, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");
    $stmt->bind_param("ississssis", $news_id, $app_name, $version, $file_size, $file_path, $checksum, $sha256_hash, $package_name, $source_priority, $source_url);
    
    if ($stmt->execute()) {
        echo json_encode([
            "success" => true,
            "tracking_id" => $mysqli->insert_id,
            "message" => "Запись добавлена в таблицу отслеживания"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Ошибка добавления в tracking: " . $stmt->error]);
    }
    exit;
}

// 📌 Проверка дублей файлов
if ($action === 'check_duplicate') {
    $news_id = intval($_GET['news_id'] ?? 0);
    $app_name = $_GET['app_name'] ?? '';
    $version = $_GET['version'] ?? '';
    $sha256_hash = $_GET['sha256_hash'] ?? null;
    $file_size = intval($_GET['file_size'] ?? 0);
    
    if ($news_id <= 0 || !$app_name || !$version) {
        echo json_encode(["error" => "Недостаточно данных"]);
        exit;
    }
    
    $duplicates = [];
    
    // Проверка по SHA-256
    if ($sha256_hash) {
        $stmt = $mysqli->prepare("
            SELECT id, version, file_size, checksum, file_path, source_priority
            FROM file_tracking
            WHERE sha256_hash = ?
            ORDER BY source_priority DESC, last_updated DESC LIMIT 1
        ");
        $stmt->bind_param("s", $sha256_hash);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($row = $result->fetch_assoc()) {
            $duplicates['sha256'] = $row;
        }
    }
    
    // Проверка по news_id + app_name + version
    $stmt = $mysqli->prepare("
        SELECT id, version, file_size, checksum, file_path, source_priority
        FROM file_tracking
        WHERE news_id = ? AND app_name = ? AND version = ?
        ORDER BY source_priority DESC, last_updated DESC LIMIT 1
    ");
    $stmt->bind_param("iss", $news_id, $app_name, $version);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        $duplicates['exact'] = $row;
    }
    
    // Проверка по размеру файла (если указан)
    if ($file_size > 0) {
        $tolerance = intval($file_size * 0.05); // 5% отклонение
        $min_size = $file_size - $tolerance;
        $max_size = $file_size + $tolerance;
        
        $stmt = $mysqli->prepare("
            SELECT id, app_name, version, file_size, file_path, source_priority, sha256_hash
            FROM file_tracking
            WHERE file_size BETWEEN ? AND ?
            ORDER BY ABS(file_size - ?) ASC, source_priority DESC, last_updated DESC
            LIMIT 5
        ");
        $stmt->bind_param("iii", $min_size, $max_size, $file_size);
        $stmt->execute();
        $result = $stmt->get_result();
        
        $size_matches = [];
        while ($row = $result->fetch_assoc()) {
            $size_matches[] = $row;
        }
        
        if (!empty($size_matches)) {
            $duplicates['size'] = $size_matches;
        }
    }
    
    echo json_encode([
        "success" => true,
        "duplicates" => $duplicates,
        "has_duplicates" => !empty($duplicates),
        "message" => empty($duplicates) ? "Дублей не найдено" : "Найдены дубли"
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// 📌 Получение информации о хранилище
if ($action === 'get_storage_info') {
    $storage_id = intval($_GET['id'] ?? 0);
    
    if ($storage_id <= 0) {
        echo json_encode(["error" => "Неверный ID хранилища"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("SELECT * FROM dle_storage WHERE id = ?");
    $stmt->bind_param("i", $storage_id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        echo json_encode([
            "success" => true,
            "storage" => [
                "id" => $row['id'],
                "name" => $row['name'],
                "type" => $row['type'],
                "accesstype" => $row['accesstype'],
                "connect_url" => $row['connect_url'],
                "connect_port" => $row['connect_port'],
                "username" => $row['username'],
                "password" => $row['password'],
                "path" => $row['path'],
                "http_url" => $row['http_url'],
                "client_key" => $row['client_key'],
                "secret_key" => $row['secret_key'],
                "bucket" => $row['bucket'],
                "region" => $row['region'],
                "default_storage" => $row['default_storage'],
                "enabled" => $row['enabled'],
                "posi" => $row['posi']
            ],
            "message" => "Информация о хранилище получена"
        ], JSON_UNESCAPED_UNICODE);
    } else {
        echo json_encode(["error" => "Хранилище не найдено"]);
    }
    exit;
}

// Функция транслитерации кириллицы
function transliterate_cyrillic($text) {
    $cyrillic_to_latin = [
        'а' => 'a', 'б' => 'b', 'в' => 'v', 'г' => 'g', 'д' => 'd', 'е' => 'e', 'ё' => 'yo',
        'ж' => 'zh', 'з' => 'z', 'и' => 'i', 'й' => 'y', 'к' => 'k', 'л' => 'l', 'м' => 'm',
        'н' => 'n', 'о' => 'o', 'п' => 'p', 'р' => 'r', 'с' => 's', 'т' => 't', 'у' => 'u',
        'ф' => 'f', 'х' => 'h', 'ц' => 'ts', 'ч' => 'ch', 'ш' => 'sh', 'щ' => 'sch',
        'ъ' => '', 'ы' => 'y', 'ь' => '', 'э' => 'e', 'ю' => 'yu', 'я' => 'ya',
        'А' => 'A', 'Б' => 'B', 'В' => 'V', 'Г' => 'G', 'Д' => 'D', 'Е' => 'E', 'Ё' => 'Yo',
        'Ж' => 'Zh', 'З' => 'Z', 'И' => 'I', 'Й' => 'Y', 'К' => 'K', 'Л' => 'L', 'М' => 'M',
        'Н' => 'N', 'О' => 'O', 'П' => 'P', 'Р' => 'R', 'С' => 'S', 'Т' => 'T', 'У' => 'U',
        'Ф' => 'F', 'Х' => 'H', 'Ц' => 'Ts', 'Ч' => 'Ch', 'Ш' => 'Sh', 'Щ' => 'Sch',
        'Ъ' => '', 'Ы' => 'Y', 'Ь' => '', 'Э' => 'E', 'Ю' => 'Yu', 'Я' => 'Ya'
    ];
    
    $result = "";
    for ($i = 0; $i < mb_strlen($text); $i++) {
        $char = mb_substr($text, $i, 1);
        if (isset($cyrillic_to_latin[$char])) {
            $result .= $cyrillic_to_latin[$char];
        } elseif ($char === '+') {
            $result .= ' ';
        } else {
            $result .= $char;
        }
    }
    
    // Убираем множественные пробелы
    $result = preg_replace('/\s+/', ' ', trim($result));
    
    return $result;
}

// ===== PARSER2 ENDPOINTS =====

// 📌 Проверка версии в поле mod-at для parser2
if ($action === 'check_mod_at') {
    $id = intval($_GET['id'] ?? 0);
    $version = $_GET['version'] ?? '';
    
    if (!$id) {
        echo json_encode(["error" => "ID не указан"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("SELECT id, xfields FROM dle_post WHERE id = ?");
    $stmt->bind_param("i", $id);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($row = $result->fetch_assoc()) {
        $xfields = $row['xfields'];
        
        // Извлекаем attachment из поля mod-at
        $attachment_name = null;
        if (preg_match('/mod-at\|\[attachment=(\d+):([^\]]+)\]/', $xfields, $matches)) {
            $attachment_name = $matches[2];
        }
        
        // Извлекаем версию из attachment
        $mod_at_version = null;
        if ($attachment_name) {
            if (preg_match('/(\d+\.\d+(?:\.\d+)?)/', $attachment_name, $version_matches)) {
                $mod_at_version = $version_matches[1];
            }
        }
        
        // Сравниваем версии
        $need_update = true;
        if ($mod_at_version && $version) {
            $need_update = version_compare($version, $mod_at_version, '>');
        }
        
        echo json_encode([
            "success" => true,
            "news_id" => $id,
            "attachment_name" => $attachment_name,
            "mod_at_version" => $mod_at_version,
            "need_update" => $need_update
        ]);
    } else {
        echo json_encode(["error" => "Запись не найдена"]);
    }
    exit;
}

// 📌 Проверка дублей для модифицированных приложений (parser2)
if ($action === 'check_duplicate_mod') {
    $news_id = intval($_GET['news_id'] ?? 0);
    $app_name = $_GET['app_name'] ?? '';
    $version = $_GET['version'] ?? '';
    $sha256_hash = $_GET['sha256_hash'] ?? '';
    $package_name = $_GET['package_name'] ?? '';
    $file_size = intval($_GET['file_size'] ?? 0);
    $table = $_GET['table'] ?? 'file_tracking_mod';
    
    $duplicates = [];
    $has_duplicates = false;
    
    // Проверяем точные дубли по SHA-256
    if ($sha256_hash) {
        $stmt = $mysqli->prepare("SELECT * FROM $table WHERE sha256_hash = ?");
        $stmt->bind_param("s", $sha256_hash);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($row = $result->fetch_assoc()) {
            $duplicates['sha256'] = $row;
            $has_duplicates = true;
        }
    }
    
    // Проверяем точные дубли по названию и версии
    if (!$has_duplicates && $news_id && $app_name && $version) {
        $stmt = $mysqli->prepare("SELECT * FROM $table WHERE news_id = ? AND app_name = ? AND version = ?");
        $stmt->bind_param("iss", $news_id, $app_name, $version);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($row = $result->fetch_assoc()) {
            $duplicates['exact'] = $row;
            $has_duplicates = true;
        }
    }
    
    // Проверяем дубли по размеру файла
    if (!$has_duplicates && $file_size > 0) {
        $tolerance_percent = 5;
        $min_size = $file_size * (1 - $tolerance_percent / 100);
        $max_size = $file_size * (1 + $tolerance_percent / 100);
        
        $stmt = $mysqli->prepare("SELECT * FROM $table WHERE file_size BETWEEN ? AND ? ORDER BY ABS(file_size - ?) LIMIT 5");
        $stmt->bind_param("ddi", $min_size, $max_size, $file_size);
        $stmt->execute();
        $result = $stmt->get_result();
        
        $size_duplicates = [];
        while ($row = $result->fetch_assoc()) {
            $size_duplicates[] = $row;
        }
        
        if (!empty($size_duplicates)) {
            $duplicates['size'] = $size_duplicates;
            $has_duplicates = true;
        }
    }
    
    echo json_encode([
        "success" => true,
        "has_duplicates" => $has_duplicates,
        "duplicates" => $duplicates
    ]);
    exit;
}

// 📌 Добавление в таблицу отслеживания модов (parser2)
if ($action === 'add_tracking_mod') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $app_name = $_POST['app_name'] ?? '';
    $version = $_POST['version'] ?? '';
    $file_size = intval($_POST['file_size'] ?? 0);
    $file_path = $_POST['file_path'] ?? '';
    $checksum = $_POST['checksum'] ?? '';
    $source_url = $_POST['source_url'] ?? '';
    $sha256_hash = $_POST['sha256_hash'] ?? '';
    $package_name = $_POST['package_name'] ?? '';
    $source_priority = intval($_POST['source_priority'] ?? 0);
    $table = $_POST['table'] ?? 'file_tracking_mod';
    
    if (!$news_id || !$app_name || !$version || !$file_size || !$file_path || !$checksum || !$source_url) {
        echo json_encode(["error" => "Не все обязательные поля заполнены"]);
        exit;
    }
    
    $stmt = $mysqli->prepare("INSERT INTO $table (news_id, app_name, version, file_size, file_path, checksum, source_url, sha256_hash, package_name, source_priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->bind_param("ississsssi", $news_id, $app_name, $version, $file_size, $file_path, $checksum, $source_url, $sha256_hash, $package_name, $source_priority);
    
    if ($stmt->execute()) {
        $tracking_id = $mysqli->insert_id;
        echo json_encode([
            "success" => true,
            "tracking_id" => $tracking_id
        ]);
    } else {
        echo json_encode(["error" => "Ошибка добавления в таблицу отслеживания: " . $mysqli->error]);
    }
    exit;
}

// 📌 Обновление поля mod-at в dle_post (parser2)
if ($action === 'update_mod_at') {
    $news_id = intval($_POST['news_id'] ?? 0);
    $file_id = intval($_POST['file_id'] ?? 0);
    $app_name = $_POST['app_name'] ?? '';
    $version = $_POST['version'] ?? '';
    $file_extension = $_POST['file_extension'] ?? '';
    
    if (!$news_id || !$file_id || !$app_name) {
        echo json_encode(["error" => "Не все обязательные поля заполнены"]);
        exit;
    }
    
    // Формируем новое значение для поля mod-at
    // Убираем пробел между app_name и version
    $attachment = "[attachment=$file_id:$app_name$version$file_extension]";
    $new_mod_at = "mod-at|$attachment||";
    
    // Получаем текущие xfields для проверки
    $stmt = $mysqli->prepare("SELECT xfields FROM dle_post WHERE id = ?");
    $stmt->bind_param("i", $news_id);
    $stmt->execute();
    $result = $stmt->get_result();
    $row = $result->fetch_assoc();
    
    if (!$row) {
        echo json_encode(["error" => "Запись с ID $news_id не найдена"]);
        exit;
    }
    
    $current_xfields = $row['xfields'];
    
    // Находим старое значение mod-at
    $old_mod_at_pattern = '/mod-at\|\[attachment=\d+:[^|]+\]\|\|/';
    if (preg_match($old_mod_at_pattern, $current_xfields, $matches)) {
        $old_mod_at = $matches[0];
        
        // Заменяем старое значение на новое
        $new_xfields = str_replace($old_mod_at, $new_mod_at, $current_xfields);
        
        // Обновляем поле mod-at в xfields
        $current_date = date('Y-m-d H:i:s');
        $stmt = $mysqli->prepare("UPDATE dle_post SET xfields = ?, date = ? WHERE id = ?");
        $stmt->bind_param("ssi", $new_xfields, $current_date, $news_id);
        
        if ($stmt->execute()) {
            echo json_encode([
                "success" => true,
                "attachment" => $attachment,
                "old_mod_at" => $old_mod_at,
                "new_mod_at" => $new_mod_at
            ]);
        } else {
            echo json_encode(["error" => "Ошибка обновления mod-at: " . $mysqli->error]);
        }
    } else {
        echo json_encode(["error" => "Поле mod-at не найдено в xfields"]);
    }
    exit;
}

// 📌 Создание таблицы отслеживания модов (parser2)
if ($action === 'create_mod_tracking_table') {
    $sql = "CREATE TABLE IF NOT EXISTS file_tracking_mod (
        id INT AUTO_INCREMENT PRIMARY KEY,
        news_id INT NOT NULL,
        app_name VARCHAR(255) NOT NULL,
        version VARCHAR(100) NOT NULL,
        file_size BIGINT NOT NULL,
        file_path VARCHAR(500) NOT NULL,
        checksum VARCHAR(32) NOT NULL,
        sha256_hash VARCHAR(64) NULL,
        package_name VARCHAR(255) NULL,
        source_priority INT DEFAULT 0,
        download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        source_url VARCHAR(500) NOT NULL,
        INDEX idx_news_id (news_id),
        INDEX idx_app_name (app_name),
        INDEX idx_sha256 (sha256_hash),
        INDEX idx_package_name (package_name),
        INDEX idx_source_priority (source_priority)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci";
    
    if ($mysqli->query($sql)) {
        echo json_encode([
            "success" => true,
            "message" => "Таблица file_tracking_mod создана успешно"
        ]);
    } else {
        echo json_encode(["error" => "Ошибка создания таблицы: " . $mysqli->error]);
    }
    exit;
}

// 📌 Проверка структуры таблицы file_tracking_mod
if ($action === 'check_mod_table_structure') {
    $table_name = 'file_tracking_mod';
    
    // Проверяем существует ли таблица
    $check_table = $mysqli->query("SHOW TABLES LIKE '$table_name'");
    if ($check_table->num_rows === 0) {
        echo json_encode([
            "success" => false,
            "error" => "Таблица $table_name не существует"
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }
    
    // Получаем структуру таблицы
    $structure = $mysqli->query("DESCRIBE $table_name");
    if (!$structure) {
        echo json_encode([
            "success" => false,
            "error" => "Не удалось получить структуру таблицы: " . $mysqli->error
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }
    
    $columns = [];
    while ($row = $structure->fetch_assoc()) {
        $columns[] = [
            "field" => $row['Field'],
            "type" => $row['Type'],
            "null" => $row['Null'],
            "key" => $row['Key'],
            "default" => $row['Default'],
            "extra" => $row['Extra']
        ];
    }
    
    // Проверяем индексы
    $indexes = $mysqli->query("SHOW INDEX FROM $table_name");
    $index_list = [];
    if ($indexes) {
        while ($index = $indexes->fetch_assoc()) {
            $index_list[] = [
                "name" => $index['Key_name'],
                "column" => $index['Column_name'],
                "unique" => $index['Non_unique'] == 0
            ];
        }
    }
    
    echo json_encode([
        "success" => true,
        "table_name" => $table_name,
        "columns" => $columns,
        "indexes" => $index_list,
        "column_count" => count($columns),
        "index_count" => count($index_list)
    ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    exit;
}

echo json_encode(["error" => "Неизвестное действие: $action"]);
?>
