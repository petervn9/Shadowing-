#include <QApplication>
#include <QMainWindow>
#include <QTabWidget>
#include <QWidget>
#include <QPushButton>
#include <QToolButton>
#include <QTableWidget>
#include <QHeaderView>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLabel>
#include <QLineEdit>
#include <QFileDialog>
#include <QFile>
#include <QTextStream>
#include <QVector>
#include <QMediaPlayer>
#include <QAudioOutput>
#include <QPainter>
#include <QPainterPath>
#include <QGroupBox>
#include <QSlider>
#include <QStyle>
#include <QRegularExpression>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QMessageBox>
#include <QDir>
#include <QFileInfo>
#include <QKeyEvent>
#include <QSet>
#include <QUrl>

#include <cmath>
#include <algorithm>
#include <random>

//===================== Data model =====================

struct Sentence
{
    int     id = 0;
    double  begin = -1.0;    // seconds, <0 = undefined
    double  end = -1.0;
    QString text;
    bool    confirm = false;
};

//===================== Helpers =====================

static QString formatTime(double sec)
{
    if (sec < 0) return QString();
    int msec = int(std::round(sec * 1000.0));
    int minutes = msec / 60000;
    msec -= minutes * 60000;
    int seconds = msec / 1000;
    msec -= seconds * 1000;
    return QString("%1:%2.%3")
        .arg(minutes, 2, 10, QLatin1Char('0'))
        .arg(seconds, 2, 10, QLatin1Char('0'))
        .arg(msec, 3, 10, QLatin1Char('0'));
}

static double parseTime(const QString& s)
{
    QString t = s.trimmed();
    if (t.isEmpty()) return -1.0;
    QStringList parts = t.split(':');
    if (parts.size() != 2) return -1.0;

    bool ok1 = false, ok2 = false;
    int minutes = parts[0].toInt(&ok1);
    double secFloat = parts[1].toDouble(&ok2);
    if (!ok1 || !ok2) return -1.0;

    return minutes * 60.0 + secFloat;
}

static int countWords(const QString& s)
{
    QStringList words =
        s.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts);
    return words.size();
}

// Simple base splitter: split by . ? ! then trim.
static QVector<QString> baseSplitSentences(const QString& text)
{
    QVector<QString> result;
    QRegularExpression re(R"(([^.!?]+[.!?]))");
    auto it = re.globalMatch(text);
    while (it.hasNext()) {
        auto m = it.next();
        QString s = m.captured(1).trimmed();
        if (!s.isEmpty())
            result.push_back(s);
    }
    if (result.isEmpty()) {
        QString s = text.trimmed();
        if (!s.isEmpty())
            result.push_back(s);
    }
    return result;
}

// Slightly “smarter” splitter following spec (chỉ ở mức đơn giản)
static QVector<QString> splitTextIntoSentencesAdvanced(const QString& text)
{
    QVector<QString> base = baseSplitSentences(text);
    QVector<QString> out;

    const int MAX_WORDS = 25;   // ~2–4s, tuỳ tốc độ đọc

    for (QString s : base) {
        s = s.trimmed();
        if (s.isEmpty()) continue;

        QStringList words =
            s.split(QRegularExpression("\\s+"), Qt::SkipEmptyParts);

        if (words.size() <= MAX_WORDS) {
            out.push_back(s);
            continue;
        }

        int start = 0;
        for (int i = 0; i < words.size(); ++i) {
            bool shouldSplit = false;
            if (i - start >= MAX_WORDS / 2) {
                QString w = words[i].toLower();
                if (w == "and" || w == "but" || w == "because"
                    || w == "so" || w == "however"
                    || words[i].endsWith(',')) {
                    shouldSplit = true;
                }
            }
            if (shouldSplit) {
                QString seg = words.mid(start, i - start + 1).join(" ");
                out.push_back(seg.trimmed());
                start = i + 1;
            }
        }
        if (start < words.size()) {
            QString seg = words.mid(start).join(" ");
            out.push_back(seg.trimmed());
        }
    }

    if (out.isEmpty())
        out = base;

    return out;
}

// JSON helpers – chung cho Setup & Practice
static bool loadLessonJson(const QString& jsonPath,
    QString& audioPath,
    QString& textPath,
    QVector<Sentence>& sentences,
    double& playSpeed,
    int& lastSentence)
{
    QFile f(jsonPath);
    if (!f.open(QIODevice::ReadOnly)) {
        QMessageBox::warning(nullptr, "Error",
            "Cannot open JSON file:\n" + jsonPath);
        return false;
    }
    QByteArray data = f.readAll();
    f.close();

    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(data, &err);
    if (err.error != QJsonParseError::NoError || !doc.isObject()) {
        QMessageBox::warning(nullptr, "Error",
            "Invalid JSON format:\n" + jsonPath);
        return false;
    }

    QJsonObject root = doc.object();
    audioPath = root["audio_path"].toString();
    textPath = root["text_path"].toString();
    playSpeed = root["play_speed"].toDouble(1.0);
    lastSentence = root["last_selected_sentence"].toInt(0);

    sentences.clear();
    QJsonArray arr = root["sentences"].toArray();
    for (int i = 0; i < arr.size(); ++i) {
        QJsonObject o = arr[i].toObject();
        Sentence s;
        s.id = o["id"].toInt(i + 1);
        s.begin = o["begin"].toDouble(-1.0);
        s.end = o["end"].toDouble(-1.0);
        s.text = o["text"].toString();
        s.confirm = o["confirmed"].toBool(false);
        sentences.push_back(s);
    }
    return true;
}

static bool saveLessonJson(const QString& jsonPath,
    const QString& audioPath,
    const QString& textPath,
    const QVector<Sentence>& sentences,
    double playSpeed,
    int lastSentence)
{
    QJsonObject root;
    root["audio_path"] = audioPath;
    root["text_path"] = textPath;
    root["play_speed"] = playSpeed;
    root["last_selected_sentence"] = lastSentence;

    QJsonArray arr;
    for (const Sentence& s : sentences) {
        QJsonObject o;
        o["id"] = s.id;
        o["begin"] = s.begin;
        o["end"] = s.end;
        o["text"] = s.text;
        o["confirmed"] = s.confirm;
        arr.push_back(o);
    }
    root["sentences"] = arr;

    QJsonDocument doc(root);
    QByteArray data = doc.toJson(QJsonDocument::Indented);

    QFile f(jsonPath);
    if (!f.open(QIODevice::WriteOnly)) {
        QMessageBox::warning(nullptr, "Error",
            "Cannot write JSON file:\n" + jsonPath);
        return false;
    }
    f.write(data);
    f.close();
    return true;
}

//===================== Waveform widget =====================

class WaveformWidget : public QWidget
{
public:
    explicit WaveformWidget(QWidget* parent = nullptr)
        : QWidget(parent)
    {
        setMinimumHeight(120);
    }

    void setDuration(double sec)
    {
        m_duration = std::max(0.0, sec);
        if (!m_hasView) {
            m_viewStart = 0.0;
            m_viewEnd = (m_duration > 0.0 ? m_duration : 1.0);
        }
        ensureMockSamples();
        update();
    }

    void setSelection(double begin, double end)
    {
        m_selBegin = begin;
        m_selEnd = end;
        update();
    }

    // zoom around current view center
    void zoomIn()
    {
        if (m_duration <= 0) return;
        double center = (m_viewStart + m_viewEnd) / 2.0;
        double len = (m_viewEnd - m_viewStart) / 1.5;
        len = std::max(len, m_duration / 100.0);
        m_viewStart = center - len / 2.0;
        m_viewEnd = center + len / 2.0;
        clampView();
        m_hasView = true;
        update();
    }

    void zoomOut()
    {
        if (m_duration <= 0) return;
        double center = (m_viewStart + m_viewEnd) / 2.0;
        double len = (m_viewEnd - m_viewStart) * 1.5;
        len = std::min(len, m_duration);
        m_viewStart = center - len / 2.0;
        m_viewEnd = center + len / 2.0;
        clampView();
        m_hasView = true;
        update();
    }

    void fitAll()
    {
        if (m_duration <= 0) return;
        m_viewStart = 0.0;
        m_viewEnd = m_duration;
        m_hasView = false;
        update();
    }

    // Auto zoom theo rule 20–60–20 (xấp xỉ)
    void autoZoomToSegment(double begin, double end)
    {
        if (m_duration <= 0.0 || begin < 0.0 || end <= begin) {
            fitAll();
            return;
        }
        double segStart = std::max(0.0, begin);
        double segEnd = std::min(m_duration, end);
        double segLen = std::max(0.05, segEnd - segStart);

        // 60% cho segment → viewLen ≈ segLen / 0.6
        double viewLen = segLen / 0.6;
        viewLen = std::min(viewLen, m_duration);
        double margin = (viewLen - segLen) / 2.0;

        double viewStart = segStart - margin;
        double viewEnd = segEnd + margin;

        if (viewStart < 0.0) {
            viewEnd -= viewStart;
            viewStart = 0.0;
        }
        if (viewEnd > m_duration) {
            double diff = viewEnd - m_duration;
            viewStart -= diff;
            viewEnd = m_duration;
            if (viewStart < 0.0) viewStart = 0.0;
        }

        m_viewStart = viewStart;
        m_viewEnd = viewEnd;
        m_hasView = true;
        update();
    }

protected:
    void paintEvent(QPaintEvent*) override
    {
        QPainter p(this);
        p.fillRect(rect(), QColor(0, 30, 60));

        if (m_duration <= 0.0) {
            p.setPen(Qt::white);
            p.drawText(rect(), Qt::AlignCenter,
                "Waveform (no audio loaded)");
            return;
        }

        QRectF r = rect().adjusted(5, 5, -5, -5);
        p.setRenderHint(QPainter::Antialiasing);

        ensureMockSamples();

        // Stylized waveform: generated mock data shaped like voice recordings
        const int steps = std::max<int>(600, r.width());
        const double halfH = r.height() * 0.48;

        // Build a closed path (top + bottom) to fill the waveform body using
        // the mock sample energy. This yields alternating quiet gaps and loud
        // bursts similar to the reference screenshots.
        QPainterPath body;
        body.moveTo(r.left(), r.center().y());
        for (int i = 0; i <= steps; ++i) {
            double tNorm = double(i) / steps;
            double tView = m_viewStart + tNorm * (m_viewEnd - m_viewStart);
            double globalNorm =
                (m_duration > 0.0 ? tView / m_duration : tNorm);

            // sample energy with tiny ripples for organic feel
            double base = sampleAt(globalNorm);
            double ripple = 0.06 * std::sin(16.0 * M_PI * tNorm)
                + 0.04 * std::sin(28.0 * M_PI * tNorm + 0.7);
            double amp = std::clamp(base + ripple, 0.02, 1.0);

            double x = r.left() + tNorm * r.width();
            double yTop = r.center().y() - amp * halfH;
            body.lineTo(x, yTop);
        }
        for (int i = steps; i >= 0; --i) {
            double tNorm = double(i) / steps;
            double tView = m_viewStart + tNorm * (m_viewEnd - m_viewStart);
            double globalNorm =
                (m_duration > 0.0 ? tView / m_duration : tNorm);

            double base = sampleAt(globalNorm);
            double ripple = 0.06 * std::sin(16.0 * M_PI * tNorm)
                + 0.04 * std::sin(28.0 * M_PI * tNorm + 0.7);
            double amp = std::clamp(base + ripple, 0.02, 1.0);

            double x = r.left() + tNorm * r.width();
            double yBot = r.center().y() + amp * halfH;
            body.lineTo(x, yBot);
        }
        body.closeSubpath();

        QLinearGradient grad(r.topLeft(), r.bottomLeft());
        grad.setColorAt(0.0, QColor(122, 240, 213));
        grad.setColorAt(1.0, QColor(0, 160, 210));
        p.fillPath(body, grad);

        QPen outline(QColor(0, 200, 220));
        outline.setWidth(2);
        p.setPen(outline);
        p.drawPath(body);

        // center baseline for balance
        p.setPen(QPen(QColor(0, 130, 190, 180), 1.5, Qt::DashLine));
        p.drawLine(QPointF(r.left(), r.center().y()), QPointF(r.right(), r.center().y()));

        // draw selected region
        if (m_selBegin >= 0.0 && m_selEnd > m_selBegin) {
            double b = std::max(m_selBegin, m_viewStart);
            double e = std::min(m_selEnd, m_viewEnd);
            if (e > b) {
                double x1 = r.left() +
                    ((b - m_viewStart) /
                        (m_viewEnd - m_viewStart)) * r.width();
                double x2 = r.left() +
                    ((e - m_viewStart) /
                        (m_viewEnd - m_viewStart)) * r.width();
                QRectF sel(x1, r.top(), x2 - x1, r.height());
                p.fillRect(sel, QColor(0, 0, 255, 60));
                p.setPen(QPen(Qt::yellow, 2));
                p.drawRect(sel);
            }
        }
    }

private:
    void clampView()
    {
        if (m_duration <= 0.0) {
            m_viewStart = 0.0;
            m_viewEnd = 1.0;
            return;
        }
        if (m_viewStart < 0.0) m_viewStart = 0.0;
        if (m_viewEnd > m_duration) m_viewEnd = m_duration;
        if (m_viewEnd - m_viewStart < m_duration / 100.0) {
            m_viewEnd = m_viewStart + m_duration / 100.0;
            if (m_viewEnd > m_duration) {
                m_viewEnd = m_duration;
                m_viewStart = m_viewEnd - m_duration / 100.0;
                if (m_viewStart < 0.0) m_viewStart = 0.0;
            }
        }
    }

    void regenerateMockSamples(int targetCount = 3600)
    {
        m_mockSamples.clear();
        m_mockSamples.reserve(targetCount);

        std::mt19937 rng(1337);
        std::uniform_real_distribution<double> uni(0.0, 1.0);
        std::uniform_real_distribution<double> quiet(0.01, 0.05);
        std::uniform_real_distribution<double> burst(0.55, 0.95);

        while (m_mockSamples.size() < targetCount) {
            bool isSilence = uni(rng) < 0.28;
            int blockLen = isSilence ? (80 + int(uni(rng) * 140))
                                     : (170 + int(uni(rng) * 320));
            double phase1 = uni(rng) * 2.0 * M_PI;
            double phase2 = uni(rng) * 2.0 * M_PI;

            for (int i = 0; i < blockLen && m_mockSamples.size() < targetCount; ++i) {
                double t = double(i) / std::max(1, blockLen - 1);
                if (isSilence) {
                    double val = quiet(rng) + 0.01 * std::sin(10.0 * M_PI * t);
                    m_mockSamples.push_back(val);
                } else {
                    double envelope = std::sin(M_PI * t);
                    double texture = 0.3 * std::sin(8.0 * M_PI * t + phase1)
                        + 0.18 * std::sin(18.0 * M_PI * t + phase2);
                    double randomPop = (uni(rng) > 0.92) ? 0.25 * uni(rng) : 0.0;
                    double core = envelope * burst(rng) + std::fabs(texture) + randomPop;
                    double air = 0.04 * uni(rng);
                    m_mockSamples.push_back(std::clamp(core + air, 0.0, 1.0));
                }
            }
        }
    }

    void ensureMockSamples()
    {
        if (m_mockSamples.isEmpty())
            regenerateMockSamples();
    }

    double sampleAt(double normalizedPos)
    {
        ensureMockSamples();
        if (m_mockSamples.isEmpty()) return 0.0;

        double clamped = std::clamp(normalizedPos, 0.0, 1.0);
        double pos = clamped * (m_mockSamples.size() - 1);
        int idx = int(pos);
        double frac = pos - idx;
        double a = m_mockSamples[idx];
        double b = m_mockSamples[std::min(idx + 1, m_mockSamples.size() - 1)];
        return a + (b - a) * frac;
    }

    double m_duration = 0.0;
    double m_selBegin = -1.0;
    double m_selEnd = -1.0;
    double m_viewStart = 0.0;
    double m_viewEnd = 1.0;
    bool   m_hasView = false;
    QVector<double> m_mockSamples;
};

//===================== Setup Tab =====================

class SetupTab : public QWidget
{
public:
    explicit SetupTab(QWidget* parent = nullptr)
        : QWidget(parent)
    {
        createUi();
        createConnections();
    }

protected:
    void keyPressEvent(QKeyEvent* ev) override
    {
        if (ev->key() == Qt::Key_Space) {
            // toggle play/pause câu hiện tại
            if (m_player->playbackState()
                == QMediaPlayer::PlayingState) {
                m_player->pause();
            }
            else {
                playSentence();
            }
            ev->accept();
            return;
        }
        if (ev->key() == Qt::Key_Left) {
            double pos = m_player->position() / 1000.0;
            pos -= 0.3;
            if (pos < 0.0) pos = 0.0;
            m_player->setPosition(qint64(pos * 1000.0));
            ev->accept();
            return;
        }
        if (ev->key() == Qt::Key_Right) {
            double pos = m_player->position() / 1000.0;
            pos += 0.3;
            if (m_duration > 0.0 &&
                pos > m_duration) pos = m_duration;
            m_player->setPosition(qint64(pos * 1000.0));
            ev->accept();
            return;
        }
        QWidget::keyPressEvent(ev);
    }

private:
    // widgets
    QTableWidget* m_table = nullptr;
    WaveformWidget* m_waveform = nullptr;

    QPushButton* m_btnOpen = nullptr;
    QPushButton* m_btnSaveSection = nullptr;
    QPushButton* m_btnSaveAs = nullptr;
    QPushButton* m_btnNewTalk = nullptr;
    QPushButton* m_btnDelete = nullptr;

    QPushButton* m_btnPrev = nullptr;
    QPushButton* m_btnPlayX = nullptr; // button “Câu X”
    QPushButton* m_btnPause = nullptr;
    QPushButton* m_btnNext = nullptr;
    QPushButton* m_btnLoop = nullptr;
    QLabel* m_lblSentenceIdx = nullptr;

    QLineEdit* m_editBegin = nullptr;
    QLineEdit* m_editEnd = nullptr;
    QPushButton* m_btnSetBegin = nullptr;
    QPushButton* m_btnSetEnd = nullptr;
    QToolButton* m_btnBeginUp = nullptr;
    QToolButton* m_btnBeginDown = nullptr;
    QToolButton* m_btnEndUp = nullptr;
    QToolButton* m_btnEndDown = nullptr;

    QPushButton* m_btnZoomIn = nullptr;
    QPushButton* m_btnZoomOut = nullptr;
    QPushButton* m_btnFit = nullptr;

    // data
    QVector<Sentence> m_sentences;
    int   m_currentRow = -1;
    bool  m_loopSentence = false;
    bool  m_updatingTable = false;

    // audio
    QMediaPlayer* m_player = nullptr;
    QAudioOutput* m_audioOut = nullptr;
    double        m_duration = 0.0;

    // paths & state
    QString m_audioPath;
    QString m_textPath;
    QString m_currentJsonPath;
    double  m_playSpeed = 1.0;

private:
    void createUi()
    {
        // --- Left button column ---
        m_btnOpen = new QPushButton("Open");
        m_btnSaveSection = new QPushButton("Save section");
        m_btnSaveAs = new QPushButton("Save as...");
        m_btnNewTalk = new QPushButton("New talk");
        m_btnDelete = new QPushButton("Delete");

        for (QPushButton* b : { m_btnOpen, m_btnSaveSection, m_btnSaveAs,
                                m_btnNewTalk, m_btnDelete }) {
            b->setMinimumHeight(40);
        }

        QVBoxLayout* leftCol = new QVBoxLayout;
        leftCol->addWidget(m_btnOpen);
        leftCol->addWidget(m_btnSaveSection);
        leftCol->addWidget(m_btnSaveAs);
        leftCol->addWidget(m_btnNewTalk);
        leftCol->addWidget(m_btnDelete);
        leftCol->addStretch();

        // --- Main table ---
        m_table = new QTableWidget(0, 5);
        QStringList headers{ "No", "Begin", "End", "Content", "Confirm" };
        m_table->setHorizontalHeaderLabels(headers);
        m_table->horizontalHeader()->setSectionResizeMode(
            0, QHeaderView::ResizeToContents);
        m_table->horizontalHeader()->setSectionResizeMode(
            1, QHeaderView::ResizeToContents);
        m_table->horizontalHeader()->setSectionResizeMode(
            2, QHeaderView::ResizeToContents);
        m_table->horizontalHeader()->setSectionResizeMode(
            3, QHeaderView::Stretch);
        m_table->horizontalHeader()->setSectionResizeMode(
            4, QHeaderView::ResizeToContents);
        m_table->setSelectionBehavior(
            QAbstractItemView::SelectRows);
        m_table->setSelectionMode(
            QAbstractItemView::SingleSelection);
        m_table->setEditTriggers(
            QAbstractItemView::DoubleClicked |
            QAbstractItemView::SelectedClicked |
            QAbstractItemView::EditKeyPressed);

        // --- Sentence control bar (green) ---
        m_btnPrev = new QPushButton;
        m_btnPlayX = new QPushButton;
        m_btnPause = new QPushButton;
        m_btnNext = new QPushButton;
        m_btnLoop = new QPushButton;

        auto iconStyle = style();
        m_btnPrev->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaSkipBackward));
        m_btnPlayX->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaPlay));
        m_btnPause->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaPause));
        m_btnNext->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaSkipForward));
        m_btnLoop->setIcon(
            iconStyle->standardIcon(QStyle::SP_BrowserReload));

        for (QPushButton* b : { m_btnPrev, m_btnPlayX, m_btnPause,
                                m_btnNext, m_btnLoop }) {
            b->setFixedSize(40, 40);
        }

        m_lblSentenceIdx = new QLabel("Câu —");
        QFont f = m_lblSentenceIdx->font();
        f.setPointSize(18);
        f.setBold(true);
        m_lblSentenceIdx->setFont(f);

        QHBoxLayout* sentCtrl = new QHBoxLayout;
        sentCtrl->addWidget(m_btnPrev);
        sentCtrl->addWidget(m_btnPlayX);
        sentCtrl->addWidget(m_btnPause);
        sentCtrl->addWidget(m_btnNext);
        sentCtrl->addWidget(m_btnLoop);
        sentCtrl->addSpacing(20);
        sentCtrl->addWidget(m_lblSentenceIdx);
        sentCtrl->addStretch();

        QFrame* sentFrame = new QFrame;
        sentFrame->setLayout(sentCtrl);
        sentFrame->setFrameShape(QFrame::Box);
        sentFrame->setStyleSheet(
            "background-color: #d8f5c0;"); // light green

        // --- Begin/End adjust group ---
        m_editBegin = new QLineEdit;
        m_editEnd = new QLineEdit;
        m_btnSetBegin = new QPushButton("Set");
        m_btnSetEnd = new QPushButton("Set");

        m_btnBeginUp = new QToolButton;
        m_btnBeginDown = new QToolButton;
        m_btnEndUp = new QToolButton;
        m_btnEndDown = new QToolButton;

        m_btnBeginUp->setArrowType(Qt::UpArrow);
        m_btnBeginDown->setArrowType(Qt::DownArrow);
        m_btnEndUp->setArrowType(Qt::UpArrow);
        m_btnEndDown->setArrowType(Qt::DownArrow);

        m_editBegin->setFixedWidth(90);
        m_editEnd->setFixedWidth(90);

        QGridLayout* timeLayout = new QGridLayout;
        timeLayout->addWidget(new QLabel("Begin"), 0, 0);
        timeLayout->addWidget(m_editBegin, 0, 1);
        timeLayout->addWidget(m_btnSetBegin, 0, 2);
        timeLayout->addWidget(m_btnBeginUp, 0, 3);
        timeLayout->addWidget(m_btnBeginDown, 0, 4);

        timeLayout->addWidget(new QLabel("End"), 1, 0);
        timeLayout->addWidget(m_editEnd, 1, 1);
        timeLayout->addWidget(m_btnSetEnd, 1, 2);
        timeLayout->addWidget(m_btnEndUp, 1, 3);
        timeLayout->addWidget(m_btnEndDown, 1, 4);

        QGroupBox* timeGroup = new QGroupBox("Begin / End");
        timeGroup->setLayout(timeLayout);

        // --- Zoom group ---
        m_btnZoomIn = new QPushButton("+");
        m_btnZoomOut = new QPushButton("-");
        m_btnFit = new QPushButton("[]");
        m_btnZoomIn->setFixedSize(40, 40);
        m_btnZoomOut->setFixedSize(40, 40);
        m_btnFit->setFixedSize(40, 40);

        QVBoxLayout* zoomLayout = new QVBoxLayout;
        zoomLayout->addWidget(m_btnZoomIn);
        zoomLayout->addWidget(m_btnZoomOut);
        zoomLayout->addWidget(m_btnFit);
        zoomLayout->addStretch();

        // --- waveform ---
        m_waveform = new WaveformWidget;

        // --- mid row (controls + time + zoom) ---
        QHBoxLayout* midRow = new QHBoxLayout;
        midRow->addWidget(sentFrame, 3);
        midRow->addWidget(timeGroup, 2);
        midRow->addLayout(zoomLayout, 0);

        QVBoxLayout* rightCol = new QVBoxLayout;
        rightCol->addWidget(m_table, 4);
        rightCol->addLayout(midRow);
        rightCol->addWidget(m_waveform, 2);

        QHBoxLayout* mainLayout = new QHBoxLayout(this);
        mainLayout->addLayout(leftCol, 0);
        mainLayout->addLayout(rightCol, 1);
        setLayout(mainLayout);

        // --- audio player ---
        m_player = new QMediaPlayer(this);
        m_audioOut = new QAudioOutput(this);
        m_player->setAudioOutput(m_audioOut);

        connect(m_player, &QMediaPlayer::durationChanged,
            this, [this](qint64 ms) {
                m_duration = ms / 1000.0;
                m_waveform->setDuration(m_duration);
                autoAssignTimesIfEmpty();
            });

        connect(m_player, &QMediaPlayer::positionChanged,
            this, [this](qint64 posMs) {
                if (!m_loopSentence) return;
                if (m_currentRow < 0 ||
                    m_currentRow >= m_sentences.size())
                    return;
                const Sentence& s = m_sentences[m_currentRow];
                if (s.begin >= 0 && s.end > s.begin) {
                    double pos = posMs / 1000.0;
                    if (pos > s.end + 0.05) {
                        m_player->setPosition(
                            qint64(s.begin * 1000.0));
                    }
                }
            });
    }

    void createConnections()
    {
        // file buttons
        connect(m_btnOpen, &QPushButton::clicked,
            this, [this]() { onOpen(); });
        connect(m_btnNewTalk, &QPushButton::clicked,
            this, [this]() { onNewTalk(); });
        connect(m_btnDelete, &QPushButton::clicked,
            this, [this]() { onDeleteRow(); });
        connect(m_btnSaveSection, &QPushButton::clicked,
            this, [this]() { onSaveSection(); });
        connect(m_btnSaveAs, &QPushButton::clicked,
            this, [this]() { onSaveAs(); });

        // table selection (single vs double click)
        connect(m_table, &QTableWidget::cellClicked,
            this, [this](int row, int) {
                onRowClicked(row);
            });
        connect(m_table, &QTableWidget::cellDoubleClicked,
            this, [this](int row, int) {
                onRowDoubleClicked(row);
            });

        // bắt thay đổi Confirm từ bảng
        connect(m_table, &QTableWidget::itemChanged,
            this, [this](QTableWidgetItem* item) {
                if (m_updatingTable) return;
                if (!item) return;
                int row = item->row();
                int col = item->column();
                if (row < 0 || row >= m_sentences.size())
                    return;
                if (col == 4) {
                    m_sentences[row].confirm =
                        (item->checkState() == Qt::Checked);
                }
                else if (col == 3) {
                    // nội dung sửa tay
                    m_sentences[row].text = item->text();
                }
            });

        // sentence controls
        connect(m_btnPrev, &QPushButton::clicked, this,
            [this]() { goToSentence(m_currentRow - 1); });
        connect(m_btnNext, &QPushButton::clicked, this,
            [this]() { goToSentence(m_currentRow + 1); });
        connect(m_btnPlayX, &QPushButton::clicked, this,
            [this]() { playSentence(); });
        connect(m_btnPause, &QPushButton::clicked, this,
            [this]() { m_player->pause(); });
        connect(m_btnLoop, &QPushButton::clicked, this,
            [this]() {
                m_loopSentence = !m_loopSentence;
                m_btnLoop->setCheckable(true);
                m_btnLoop->setChecked(m_loopSentence);
            });

        // time adjust
        connect(m_btnSetBegin, &QPushButton::clicked, this,
            [this]() { setTimeFromPlayHead(true); });
        connect(m_btnSetEnd, &QPushButton::clicked, this,
            [this]() { setTimeFromPlayHead(false); });

        connect(m_btnBeginUp, &QToolButton::clicked,
            this, [this]() { adjustTime(true, +0.010); });
        connect(m_btnBeginDown, &QToolButton::clicked,
            this, [this]() { adjustTime(true, -0.010); });
        connect(m_btnEndUp, &QToolButton::clicked,
            this, [this]() { adjustTime(false, +0.010); });
        connect(m_btnEndDown, &QToolButton::clicked,
            this, [this]() { adjustTime(false, -0.010); });

        // direct edit Begin/End
        connect(m_editBegin, &QLineEdit::editingFinished,
            this, [this]() { setTimeFromEditor(true); });
        connect(m_editEnd, &QLineEdit::editingFinished,
            this, [this]() { setTimeFromEditor(false); });

        // zoom
        connect(m_btnZoomIn, &QPushButton::clicked, this,
            [this]() { m_waveform->zoomIn();  });
        connect(m_btnZoomOut, &QPushButton::clicked, this,
            [this]() { m_waveform->zoomOut(); });
        connect(m_btnFit, &QPushButton::clicked, this,
            [this]() { m_waveform->fitAll();  });
    }

    // -------- logic --------

    void onOpen()
    {
        QMessageBox box(this);
        box.setWindowTitle("Open lesson");
        box.setText("Open new lesson from audio + text\n"
            "or reopen from JSON section file?");
        QPushButton* btnAT =
            box.addButton("Audio + Text", QMessageBox::AcceptRole);
        QPushButton* btnJson =
            box.addButton("JSON section", QMessageBox::ActionRole);
        box.addButton(QMessageBox::Cancel);
        box.exec();

        if (box.clickedButton() == btnJson) {
            openFromJson();
        }
        else if (box.clickedButton() == btnAT) {
            openAudioText();
        }
    }

    void openAudioText()
    {
        QString audioPath = QFileDialog::getOpenFileName(
            this, "Open audio file", QString(),
            "Audio files (*.mp3 *.wav *.m4a *.flac);;All files (*.*)");
        if (audioPath.isEmpty())
            return;

        QString textPath = QFileDialog::getOpenFileName(
            this, "Open text file", QFileInfo(audioPath).absolutePath(),
            "Text files (*.txt);;All files (*.*)");
        if (textPath.isEmpty())
            return;

        // load text
        QFile f(textPath);
        if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) {
            QMessageBox::warning(this, "Error",
                "Cannot open text file.");
            return;
        }
        QTextStream in(&f);
        QString allText = in.readAll();
        f.close();

        auto parts = splitTextIntoSentencesAdvanced(allText);
        m_sentences.clear();
        int id = 1;
        for (const QString& s : parts) {
            Sentence sen;
            sen.id = id++;
            sen.text = s.trimmed();
            m_sentences.push_back(sen);
        }

        m_audioPath = audioPath;
        m_textPath = textPath;
        m_currentJsonPath.clear();

        // load audio
        m_player->setSource(QUrl::fromLocalFile(audioPath));
        m_player->stop();

        rebuildTable();
        if (!m_sentences.isEmpty()) {
            goToSentence(0);
        }

        // Tìm JSON cùng tên
        QFileInfo info(audioPath);
        QDir dir = info.dir();
        QString base = info.completeBaseName();
        QStringList candidates =
            dir.entryList(QStringList{ base + "*.json" },
                QDir::Files);
        if (!candidates.isEmpty()) {
            QString jsonPath = dir.absoluteFilePath(candidates.first());
            auto ret = QMessageBox::question(
                this, "Found JSON",
                QString("Found setup file:\n%1\n"
                    "Load this setup instead?")
                .arg(jsonPath),
                QMessageBox::Yes | QMessageBox::No);
            if (ret == QMessageBox::Yes) {
                loadFromJson(jsonPath);
            }
        }
    }

    void openFromJson()
    {
        QString jsonPath = QFileDialog::getOpenFileName(
            this, "Open JSON section file", QString(),
            "JSON files (*.json);;All files (*.*)");
        if (jsonPath.isEmpty()) return;

        loadFromJson(jsonPath);
    }

    void loadFromJson(const QString& jsonPath)
    {
        QString audio, text;
        double speed = 1.0;
        int lastSent = 0;
        QVector<Sentence> sents;

        if (!loadLessonJson(jsonPath, audio, text,
            sents, speed, lastSent))
            return;

        // kiểm tra audio tồn tại
        if (!QFile::exists(audio)) {
            QMessageBox::information(
                this, "Audio missing",
                "Audio file not found:\n" + audio +
                "\nPlease select the new audio file.");
            QString newAudio = QFileDialog::getOpenFileName(
                this, "Select audio file", QString(),
                "Audio files (*.mp3 *.wav *.m4a *.flac);;All files (*.*)");
            if (newAudio.isEmpty()) return;
            audio = newAudio;
        }

        m_audioPath = audio;
        m_textPath = text;
        m_playSpeed = speed;
        m_currentJsonPath = jsonPath;

        m_sentences = sents;

        m_player->setSource(QUrl::fromLocalFile(m_audioPath));
        m_player->setPlaybackRate(m_playSpeed);
        m_player->stop();

        rebuildTable();

        if (!m_sentences.isEmpty()) {
            if (lastSent < 0 || lastSent >= m_sentences.size())
                lastSent = 0;
            goToSentence(lastSent);
        }
    }

    void onSaveSection()
    {
        if (m_audioPath.isEmpty() || m_sentences.isEmpty()) {
            QMessageBox::information(this, "Info",
                "Nothing to save.");
            return;
        }
        if (m_currentJsonPath.isEmpty()) {
            onSaveAs();
            return;
        }
        saveCurrentLesson(m_currentJsonPath);
    }

    void onSaveAs()
    {
        if (m_audioPath.isEmpty() || m_sentences.isEmpty()) {
            QMessageBox::information(this, "Info",
                "Nothing to save.");
            return;
        }

        QString dir = QFileInfo(m_audioPath).absolutePath();
        QString base = QFileInfo(m_audioPath).completeBaseName();
        QString defName = dir + "/" + base + ".json";

        QString jsonPath = QFileDialog::getSaveFileName(
            this, "Save JSON section", defName,
            "JSON files (*.json);;All files (*.*)");
        if (jsonPath.isEmpty()) return;

        if (!jsonPath.endsWith(".json", Qt::CaseInsensitive))
            jsonPath += ".json";

        if (saveCurrentLesson(jsonPath)) {
            m_currentJsonPath = jsonPath;
        }
    }

    bool saveCurrentLesson(const QString& jsonPath)
    {
        int lastSent = std::max(0, m_currentRow);
        if (!saveLessonJson(jsonPath, m_audioPath, m_textPath,
            m_sentences, m_playSpeed, lastSent)) {
            return false;
        }
        QMessageBox::information(this, "Saved",
            "JSON has been saved:\n" + jsonPath);
        return true;
    }

    void onNewTalk()
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size()) {
            // thêm vào cuối
            Sentence s;
            s.id = m_sentences.size() + 1;
            m_sentences.push_back(s);
            rebuildTable();
            goToSentence(m_sentences.size() - 1);
            return;
        }

        Sentence s;
        s.id = m_currentRow + 2;
        m_sentences.insert(m_currentRow + 1, s);

        // renumber
        for (int i = 0; i < m_sentences.size(); ++i)
            m_sentences[i].id = i + 1;

        rebuildTable();
        goToSentence(m_currentRow + 1);
    }

    void onDeleteRow()
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size())
            return;
        m_sentences.removeAt(m_currentRow);
        // renumber
        for (int i = 0; i < m_sentences.size(); ++i)
            m_sentences[i].id = i + 1;

        rebuildTable();
        if (m_currentRow >= m_sentences.size())
            m_currentRow = m_sentences.size() - 1;
        if (m_currentRow >= 0)
            goToSentence(m_currentRow);
        else {
            m_lblSentenceIdx->setText("Câu —");
            m_editBegin->clear();
            m_editEnd->clear();
            m_waveform->setSelection(-1, -1);
        }
    }

    void onRowClicked(int row)
    {
        if (row < 0 || row >= m_sentences.size())
            return;
        goToSentence(row);
    }

    void onRowDoubleClicked(int row)
    {
        if (row < 0 || row >= m_sentences.size())
            return;
        goToSentence(row);
        playSentence();
    }

    void goToSentence(int row)
    {
        if (row < 0 || row >= m_sentences.size())
            return;
        m_currentRow = row;

        m_updatingTable = true;
        m_table->setCurrentCell(row, 0);
        m_table->selectRow(row);
        m_updatingTable = false;

        m_lblSentenceIdx->setText(
            QString("Câu %1").arg(row + 1));

        const Sentence& s = m_sentences[row];
        m_editBegin->setText(formatTime(s.begin));
        m_editEnd->setText(formatTime(s.end));
        m_waveform->setSelection(s.begin, s.end);
        if (s.begin >= 0 && s.end > s.begin)
            m_waveform->autoZoomToSegment(s.begin, s.end);
    }

    void playSentence()
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size()) {
            m_player->play();
            return;
        }

        const Sentence& s = m_sentences[m_currentRow];
        if (s.begin >= 0.0)
            m_player->setPosition(
                qint64(s.begin * 1000.0));
        m_player->setPlaybackRate(m_playSpeed);
        m_player->play();
    }

    void setTimeFromPlayHead(bool isBegin)
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size())
            return;

        double t = m_player->position() / 1000.0;
        Sentence& s = m_sentences[m_currentRow];
        bool changed = false;

        if (isBegin) {
            if (std::abs(s.begin - t) > 1e-4) {
                s.begin = t;
                changed = true;
            }
        }
        else {
            if (std::abs(s.end - t) > 1e-4) {
                s.end = t;
                changed = true;
            }
        }

        if (changed) {
            if (s.confirm) {
                s.confirm = false;
                if (auto* it = m_table->item(m_currentRow, 4)) {
                    m_updatingTable = true;
                    it->setCheckState(Qt::Unchecked);
                    m_updatingTable = false;
                }
            }
            updateRow(m_currentRow);
            m_waveform->setSelection(s.begin, s.end);
        }
    }

    void setTimeFromEditor(bool isBegin)
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size())
            return;

        double t = parseTime(isBegin ?
            m_editBegin->text()
            : m_editEnd->text());
        if (t < 0.0) return;

        Sentence& s = m_sentences[m_currentRow];
        bool changed = false;

        if (isBegin) {
            if (std::abs(s.begin - t) > 1e-4) {
                s.begin = t;
                changed = true;
            }
        }
        else {
            if (std::abs(s.end - t) > 1e-4) {
                s.end = t;
                changed = true;
            }
        }

        if (changed) {
            if (s.confirm) {
                s.confirm = false;
                if (auto* it = m_table->item(m_currentRow, 4)) {
                    m_updatingTable = true;
                    it->setCheckState(Qt::Unchecked);
                    m_updatingTable = false;
                }
            }
            updateRow(m_currentRow);
            m_waveform->setSelection(s.begin, s.end);
        }
    }

    void adjustTime(bool isBegin, double delta)
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size())
            return;
        Sentence& s = m_sentences[m_currentRow];
        double* val = isBegin ? &s.begin : &s.end;
        if (*val < 0.0) *val = 0.0;
        *val += delta;
        if (*val < 0.0) *val = 0.0;

        if (s.confirm) {
            s.confirm = false;
            if (auto* it = m_table->item(m_currentRow, 4)) {
                m_updatingTable = true;
                it->setCheckState(Qt::Unchecked);
                m_updatingTable = false;
            }
        }

        if (isBegin)
            m_editBegin->setText(formatTime(s.begin));
        else
            m_editEnd->setText(formatTime(s.end));

        updateRow(m_currentRow);
        m_waveform->setSelection(s.begin, s.end);
    }

    void autoAssignTimesIfEmpty()
    {
        // Thay cho Whisper: tạm gán Begin/End theo số từ
        if (m_duration <= 0.0) return;
        if (m_sentences.isEmpty()) return;

        bool allUnset = true;
        for (const Sentence& s : m_sentences) {
            if (s.begin >= 0.0 && s.end > s.begin) {
                allUnset = false;
                break;
            }
        }
        if (!allUnset) return;

        int totalWords = 0;
        QVector<int> wordCounts;
        for (const Sentence& s : m_sentences) {
            int c = countWords(s.text);
            if (c <= 0) c = 1;
            wordCounts.push_back(c);
            totalWords += c;
        }
        if (totalWords <= 0) totalWords = m_sentences.size();

        double t = 0.0;
        for (int i = 0; i < m_sentences.size(); ++i) {
            double frac =
                double(wordCounts[i]) / double(totalWords);
            double len = m_duration * frac;
            m_sentences[i].begin = t;
            m_sentences[i].end = t + len;
            t += len;
        }
        rebuildTable();
        if (m_currentRow >= 0 &&
            m_currentRow < m_sentences.size()) {
            m_waveform->setSelection(
                m_sentences[m_currentRow].begin,
                m_sentences[m_currentRow].end);
        }
    }

    void rebuildTable()
    {
        m_updatingTable = true;
        m_table->setRowCount(m_sentences.size());
        for (int i = 0; i < m_sentences.size(); ++i) {
            const Sentence& s = m_sentences[i];

            auto* noItem =
                new QTableWidgetItem(
                    QString("Câu %1").arg(i + 1));
            auto* beginItem =
                new QTableWidgetItem(
                    formatTime(s.begin));
            auto* endItem =
                new QTableWidgetItem(
                    formatTime(s.end));
            auto* contentItem =
                new QTableWidgetItem(s.text);
            auto* confirmItem = new QTableWidgetItem;
            confirmItem->setFlags(confirmItem->flags()
                | Qt::ItemIsUserCheckable);
            confirmItem->setCheckState(
                s.confirm ? Qt::Checked : Qt::Unchecked);

            m_table->setItem(i, 0, noItem);
            m_table->setItem(i, 1, beginItem);
            m_table->setItem(i, 2, endItem);
            m_table->setItem(i, 3, contentItem);
            m_table->setItem(i, 4, confirmItem);
        }
        m_updatingTable = false;
    }

    void updateRow(int row)
    {
        if (row < 0 || row >= m_sentences.size()) return;
        const Sentence& s = m_sentences[row];
        if (auto* it = m_table->item(row, 1)) {
            m_updatingTable = true;
            it->setText(formatTime(s.begin));
            m_updatingTable = false;
        }
        if (auto* it = m_table->item(row, 2)) {
            m_updatingTable = true;
            it->setText(formatTime(s.end));
            m_updatingTable = false;
        }
    }
};

//===================== Practice Tab =====================

class PracticeTab : public QWidget
{
public:
    explicit PracticeTab(QWidget* parent = nullptr)
        : QWidget(parent)
    {
        createUi();
        createConnections();
    }

private:
    // UI
    QTableWidget* m_tblSent = nullptr;
    QTableWidget* m_tblVocab = nullptr;
    WaveformWidget* m_wave = nullptr;

    QPushButton* m_btnOpen = nullptr;
    QPushButton* m_btnSaveSection = nullptr;
    QPushButton* m_btnSaveAs = nullptr;
    QPushButton* m_btnNewTalk = nullptr;
    QPushButton* m_btnDelete = nullptr;

    QPushButton* m_btnPrev = nullptr;
    QPushButton* m_btnPlayX = nullptr;
    QPushButton* m_btnPause = nullptr;
    QPushButton* m_btnNext = nullptr;
    QPushButton* m_btnLoop = nullptr;
    QLabel* m_lblIdx = nullptr;

    QVector<QPushButton*> m_speedButtons;
    double m_playSpeed = 1.0;

    QPushButton* m_btnZIn = nullptr;
    QPushButton* m_btnZOut = nullptr;
    QPushButton* m_btnFit = nullptr;

    // data
    QVector<Sentence> m_sentences;
    int   m_currentRow = -1;
    bool  m_loopSentence = false;
    bool  m_updatingTable = false;

    // audio
    QMediaPlayer* m_player = nullptr;
    QAudioOutput* m_audioOut = nullptr;
    double        m_duration = 0.0;
    QString       m_audioPath;
    QString       m_textPath;
    QString       m_jsonPath;

private:
    void createUi()
    {
        // Left buttons
        m_btnOpen = new QPushButton("Open");
        m_btnSaveSection = new QPushButton("Save section");
        m_btnSaveAs = new QPushButton("Save as...");
        m_btnNewTalk = new QPushButton("New talk");
        m_btnDelete = new QPushButton("Delete");

        for (QPushButton* b : { m_btnOpen, m_btnSaveSection,
                                m_btnSaveAs, m_btnNewTalk,
                                m_btnDelete }) {
            b->setMinimumHeight(40);
        }

        QVBoxLayout* leftCol = new QVBoxLayout;
        leftCol->addWidget(m_btnOpen);
        leftCol->addWidget(m_btnSaveSection);
        leftCol->addWidget(m_btnSaveAs);
        leftCol->addWidget(m_btnNewTalk);
        leftCol->addWidget(m_btnDelete);
        leftCol->addStretch();

        // Sentence table: No / Content / Hide / Show
        m_tblSent = new QTableWidget(0, 4);
        QStringList headers1{ "No", "Content", "Hide", "Show" };
        m_tblSent->setHorizontalHeaderLabels(headers1);
        m_tblSent->horizontalHeader()->setSectionResizeMode(
            0, QHeaderView::ResizeToContents);
        m_tblSent->horizontalHeader()->setSectionResizeMode(
            1, QHeaderView::Stretch);
        m_tblSent->horizontalHeader()->setSectionResizeMode(
            2, QHeaderView::ResizeToContents);
        m_tblSent->horizontalHeader()->setSectionResizeMode(
            3, QHeaderView::ResizeToContents);
        m_tblSent->setSelectionBehavior(
            QAbstractItemView::SelectRows);
        m_tblSent->setSelectionMode(
            QAbstractItemView::SingleSelection);

        // Vocab table: đơn giản
        m_tblVocab = new QTableWidget(0, 3);
        QStringList headers2{ "No.", "Word", "Meaning (VI)" };
        m_tblVocab->setHorizontalHeaderLabels(headers2);
        m_tblVocab->horizontalHeader()->setSectionResizeMode(
            0, QHeaderView::ResizeToContents);
        m_tblVocab->horizontalHeader()->setSectionResizeMode(
            1, QHeaderView::ResizeToContents);
        m_tblVocab->horizontalHeader()->setSectionResizeMode(
            2, QHeaderView::Stretch);

        QHBoxLayout* topRow = new QHBoxLayout;
        topRow->addWidget(m_tblSent, 3);
        topRow->addWidget(m_tblVocab, 2);

        // Sentence control bar
        m_btnPrev = new QPushButton;
        m_btnPlayX = new QPushButton;
        m_btnPause = new QPushButton;
        m_btnNext = new QPushButton;
        m_btnLoop = new QPushButton;
        m_lblIdx = new QLabel("Câu —");

        auto iconStyle = style();
        m_btnPrev->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaSkipBackward));
        m_btnPlayX->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaPlay));
        m_btnPause->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaPause));
        m_btnNext->setIcon(
            iconStyle->standardIcon(QStyle::SP_MediaSkipForward));
        m_btnLoop->setIcon(
            iconStyle->standardIcon(QStyle::SP_BrowserReload));

        for (QPushButton* b : { m_btnPrev, m_btnPlayX, m_btnPause,
                                m_btnNext, m_btnLoop }) {
            b->setFixedSize(40, 40);
        }

        QFont f = m_lblIdx->font();
        f.setPointSize(18);
        f.setBold(true);
        m_lblIdx->setFont(f);

        QHBoxLayout* sentCtrl = new QHBoxLayout;
        sentCtrl->addWidget(m_btnPrev);
        sentCtrl->addWidget(m_btnPlayX);
        sentCtrl->addWidget(m_btnPause);
        sentCtrl->addWidget(m_btnNext);
        sentCtrl->addWidget(m_btnLoop);
        sentCtrl->addSpacing(20);
        sentCtrl->addWidget(m_lblIdx);
        sentCtrl->addStretch();

        QWidget* sentBar = new QWidget;
        sentBar->setLayout(sentCtrl);
        sentBar->setStyleSheet(
            "background-color: #d8f5c0; border:1px solid gray;");

        // Speed buttons
        QHBoxLayout* speedLayout = new QHBoxLayout;
        QStringList speeds{ "0.5x", "0.75x", "1.0", "1.2x", "1.5x" };
        for (const QString& s : speeds) {
            auto* btn = new QPushButton(s);
            btn->setMinimumWidth(60);
            if (s == "1.0") {
                btn->setStyleSheet("background-color: yellow;");
            }
            m_speedButtons.push_back(btn);
            speedLayout->addWidget(btn);
        }
        speedLayout->addStretch();

        // Zoom buttons
        m_btnZIn = new QPushButton("+");
        m_btnZOut = new QPushButton("-");
        m_btnFit = new QPushButton("[]");
        m_btnZIn->setFixedSize(40, 40);
        m_btnZOut->setFixedSize(40, 40);
        m_btnFit->setFixedSize(40, 40);
        QHBoxLayout* zoomLayout = new QHBoxLayout;
        zoomLayout->addStretch();
        zoomLayout->addWidget(m_btnZIn);
        zoomLayout->addWidget(m_btnZOut);
        zoomLayout->addWidget(m_btnFit);

        // waveform
        m_wave = new WaveformWidget;

        QVBoxLayout* rightCol = new QVBoxLayout;
        rightCol->addLayout(topRow, 3);
        rightCol->addWidget(sentBar);
        rightCol->addLayout(speedLayout);
        rightCol->addLayout(zoomLayout);
        rightCol->addWidget(m_wave, 2);

        QHBoxLayout* main = new QHBoxLayout(this);
        main->addLayout(leftCol, 0);
        main->addLayout(rightCol, 1);
        setLayout(main);

        // audio
        m_player = new QMediaPlayer(this);
        m_audioOut = new QAudioOutput(this);
        m_player->setAudioOutput(m_audioOut);

        connect(m_player, &QMediaPlayer::durationChanged,
            this, [this](qint64 ms) {
                m_duration = ms / 1000.0;
                m_wave->setDuration(m_duration);
            });
        connect(m_player, &QMediaPlayer::positionChanged,
            this, [this](qint64 posMs) {
                if (!m_loopSentence) return;
                if (m_currentRow < 0 ||
                    m_currentRow >= m_sentences.size())
                    return;
                const Sentence& s = m_sentences[m_currentRow];
                if (s.begin >= 0 && s.end > s.begin) {
                    double pos = posMs / 1000.0;
                    if (pos > s.end + 0.05) {
                        m_player->setPosition(
                            qint64(s.begin * 1000.0));
                    }
                }
            });
    }

    void createConnections()
    {
        connect(m_btnOpen, &QPushButton::clicked,
            this, [this]() { onOpen(); });

        // các nút khác hiện để trống (nếu cần sau này)
        connect(m_btnSaveSection, &QPushButton::clicked,
            this, [this]() {
                QMessageBox::information(this, "Info",
                    "Practice tab currently "
                    "does not save JSON.");
            });

        connect(m_tblSent, &QTableWidget::cellClicked,
            this, [this](int row, int col) {
                if (col == 2 || col == 3) {
                    handleHideShowClicked(row, col);
                }
                else {
                    selectSentence(row, false);
                }
            });
        connect(m_tblSent, &QTableWidget::cellDoubleClicked,
            this, [this](int row, int) {
                selectSentence(row, true);
            });

        // sentence controls
        connect(m_btnPrev, &QPushButton::clicked,
            this, [this]() { selectSentence(
                m_currentRow - 1, false); });
        connect(m_btnNext, &QPushButton::clicked,
            this, [this]() { selectSentence(
                m_currentRow + 1, false); });
        connect(m_btnPlayX, &QPushButton::clicked,
            this, [this]() { playSentence(); });
        connect(m_btnPause, &QPushButton::clicked,
            this, [this]() { m_player->pause(); });
        connect(m_btnLoop, &QPushButton::clicked,
            this, [this]() {
                m_loopSentence = !m_loopSentence;
                m_btnLoop->setCheckable(true);
                m_btnLoop->setChecked(m_loopSentence);
            });

        // speed
        for (QPushButton* b : m_speedButtons) {
            connect(b, &QPushButton::clicked,
                this, [this, b]() { onSpeedButton(b); });
        }

        // zoom
        connect(m_btnZIn, &QPushButton::clicked,
            this, [this]() { m_wave->zoomIn(); });
        connect(m_btnZOut, &QPushButton::clicked,
            this, [this]() { m_wave->zoomOut(); });
        connect(m_btnFit, &QPushButton::clicked,
            this, [this]() { m_wave->fitAll(); });
    }

    void onOpen()
    {
        QString jsonPath = QFileDialog::getOpenFileName(
            this, "Open JSON section file", QString(),
            "JSON files (*.json);;All files (*.*)");
        if (jsonPath.isEmpty()) return;

        QString audio, text;
        double speed = 1.0;
        int lastSent = 0;
        QVector<Sentence> sents;

        if (!loadLessonJson(jsonPath, audio, text,
            sents, speed, lastSent))
            return;

        if (!QFile::exists(audio)) {
            QMessageBox::information(
                this, "Audio missing",
                "Audio file not found:\n" + audio +
                "\nPlease select new audio.");
            QString newAudio = QFileDialog::getOpenFileName(
                this, "Select audio file", QString(),
                "Audio files (*.mp3 *.wav *.m4a *.flac);;All files (*.*)");
            if (newAudio.isEmpty()) return;
            audio = newAudio;
        }

        m_audioPath = audio;
        m_textPath = text;
        m_jsonPath = jsonPath;
        m_playSpeed = speed;
        m_sentences = sents;

        m_player->setSource(QUrl::fromLocalFile(m_audioPath));
        m_player->setPlaybackRate(m_playSpeed);
        m_player->stop();

        rebuildSentenceTable();
        rebuildVocabTable();

        if (!m_sentences.isEmpty()) {
            if (lastSent < 0 || lastSent >= m_sentences.size())
                lastSent = 0;
            selectSentence(lastSent, false);
        }
    }

    void rebuildSentenceTable()
    {
        m_updatingTable = true;
        m_tblSent->setRowCount(m_sentences.size());
        for (int i = 0; i < m_sentences.size(); ++i) {
            const Sentence& s = m_sentences[i];

            auto* noItem =
                new QTableWidgetItem(
                    QString("Câu %1").arg(i + 1));
            auto* contentItem =
                new QTableWidgetItem(s.text);

            auto* hideItem = new QTableWidgetItem;
            hideItem->setFlags(hideItem->flags() |
                Qt::ItemIsUserCheckable);
            hideItem->setCheckState(Qt::Unchecked);

            auto* showItem = new QTableWidgetItem;
            showItem->setFlags(showItem->flags() |
                Qt::ItemIsUserCheckable);
            showItem->setCheckState(Qt::Checked);

            m_tblSent->setItem(i, 0, noItem);
            m_tblSent->setItem(i, 1, contentItem);
            m_tblSent->setItem(i, 2, hideItem);
            m_tblSent->setItem(i, 3, showItem);
        }
        m_updatingTable = false;
    }

    void rebuildVocabTable()
    {
        // tạo list từ đơn giản (unique, lower case)
        QSet<QString> wordSet;
        for (const Sentence& s : m_sentences) {
            QString tmp = s.text;
            tmp.replace(QRegularExpression("[^A-Za-z']"), " ");
            QStringList words = tmp.split(
                QRegularExpression("\\s+"),
                Qt::SkipEmptyParts);
            for (QString w : words) {
                w = w.toLower();
                if (!w.isEmpty())
                    wordSet.insert(w);
            }
        }
        QStringList wordList = QStringList(wordSet.begin(), wordSet.end());
        std::sort(wordList.begin(), wordList.end());

        m_tblVocab->setRowCount(wordList.size());
        for (int i = 0; i < wordList.size(); ++i) {
            m_tblVocab->setItem(
                i, 0,
                new QTableWidgetItem(QString::number(i + 1)));
            m_tblVocab->setItem(
                i, 1,
                new QTableWidgetItem(wordList[i]));
            m_tblVocab->setItem(
                i, 2,
                new QTableWidgetItem("")); // Meaning VI – để trống
        }
    }

    void selectSentence(int row, bool play)
    {
        if (row < 0 || row >= m_sentences.size())
            return;
        m_currentRow = row;

        m_updatingTable = true;
        m_tblSent->setCurrentCell(row, 0);
        m_tblSent->selectRow(row);
        m_updatingTable = false;

        m_lblIdx->setText(QString("Câu %1").arg(row + 1));

        const Sentence& s = m_sentences[row];
        m_wave->setSelection(s.begin, s.end);
        if (s.begin >= 0 && s.end > s.begin)
            m_wave->autoZoomToSegment(s.begin, s.end);

        if (play)
            playSentence();
    }

    void playSentence()
    {
        if (m_currentRow < 0 ||
            m_currentRow >= m_sentences.size()) {
            m_player->play();
            return;
        }
        const Sentence& s = m_sentences[m_currentRow];
        if (s.begin >= 0.0)
            m_player->setPosition(
                qint64(s.begin * 1000.0));
        m_player->setPlaybackRate(m_playSpeed);
        m_player->play();
    }

    void handleHideShowClicked(int row, int col)
    {
        if (row < 0 || row >= m_tblSent->rowCount())
            return;
        if (col != 2 && col != 3) return;

        m_updatingTable = true;
        QTableWidgetItem* hideItem = m_tblSent->item(row, 2);
        QTableWidgetItem* showItem = m_tblSent->item(row, 3);

        if (col == 2) {
            hideItem->setCheckState(Qt::Checked);
            showItem->setCheckState(Qt::Unchecked);
            if (auto* content = m_tblSent->item(row, 1)) {
                content->setText("_________________________");
            }
        }
        else {
            hideItem->setCheckState(Qt::Unchecked);
            showItem->setCheckState(Qt::Checked);
            if (auto* content = m_tblSent->item(row, 1)) {
                content->setText(m_sentences[row].text);
            }
        }
        m_updatingTable = false;
    }

    void onSpeedButton(QPushButton* btn)
    {
        QString txt = btn->text(); // ví dụ "1.2x"
        QString num = txt;
        num.remove('x');
        bool ok = false;
        double v = num.toDouble(&ok);
        if (!ok || v <= 0.0)
            return;

        m_playSpeed = v;
        m_player->setPlaybackRate(m_playSpeed);

        // highlight button
        for (QPushButton* b : m_speedButtons) {
            if (b == btn)
                b->setStyleSheet("background-color: yellow;");
            else
                b->setStyleSheet("");
        }
    }
};

//===================== Main Window =====================

class MainWindow : public QMainWindow
{
public:
    explicit MainWindow(QWidget* parent = nullptr)
        : QMainWindow(parent)
    {
        setWindowTitle("Shadowing English");

        QTabWidget* tabs = new QTabWidget;
        tabs->addTab(new SetupTab, "Setup");
        tabs->addTab(new PracticeTab, "Practice");

        setCentralWidget(tabs);
        resize(1280, 720);
    }
};

//===================== main() =====================

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);
    MainWindow w;
    w.show();
    return app.exec();
}
