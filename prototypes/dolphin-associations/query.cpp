// Read-only acceptance probe for the installed KDE service ordering.
// Build/run against the target KDE version; never shipped as an application dependency.
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <KApplicationTrader>
#include <KService>
#include <cstdio>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    QJsonObject result;
    for (const auto &mime : app.arguments().mid(1)) {
        QJsonArray offers;
        for (const auto &service : KApplicationTrader::queryByMimeType(mime))
            offers.append(service->storageId());
        result.insert(mime, offers);
    }
    auto data = QJsonDocument(result).toJson();
    std::fwrite(data.constData(), 1, data.size(), stdout);
}
